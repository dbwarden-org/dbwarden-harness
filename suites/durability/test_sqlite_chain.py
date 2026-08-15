import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from tools.migration_player import MigrationPlayer


def test_sqlite_migration_chain_can_apply_and_rollback(tmp_path: Path):
    player = MigrationPlayer(f"sqlite:///{tmp_path / 'app.db'}", tmp_path)
    player.init_and_configure()
    migration_dir = tmp_path / "migrations" / "primary"
    migration_dir.mkdir(parents=True, exist_ok=True)
    (migration_dir / "primary__0001_initial.sql").write_text(
        "-- upgrade\nCREATE TABLE users (id INTEGER PRIMARY KEY);\n"
        "-- rollback\nDROP TABLE users;\n",
        encoding="utf-8",
    )
    player.migrate()

    (migration_dir / "primary__0002_orders.sql").write_text(
        "-- upgrade\nCREATE TABLE orders (id INTEGER PRIMARY KEY);\n"
        "-- rollback\nDROP TABLE orders;\n",
        encoding="utf-8",
    )
    player.migrate()
    player.rollback()

    status = player.status()
    assert status.returncode == 0


def test_sqlite_fifty_migration_chain_supports_subset_replay(tmp_path: Path):
    database = tmp_path / "durable.db"
    player = MigrationPlayer(f"sqlite:///{database}", tmp_path)
    player.init_and_configure()
    migration_dir = tmp_path / "migrations" / "primary"
    migration_dir.mkdir(parents=True, exist_ok=True)

    for number in range(1, 51):
        table = f"chain_{number:03d}"
        (migration_dir / f"primary__{number:04d}_chain.sql").write_text(
            f"-- upgrade\nCREATE TABLE {table} (id INTEGER PRIMARY KEY);\n"
            f"-- rollback\nDROP TABLE {table};\n",
            encoding="utf-8",
        )

    assert player.migrate().returncode == 0
    with closing(sqlite3.connect(database)) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE 'chain_%'"
            )
        }
    assert len(tables) == 50

    assert player.rollback(10).returncode == 0
    assert player.migrate().returncode == 0
    with closing(sqlite3.connect(database)) as connection:
        replayed_tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE 'chain_%'"
            )
        }
    assert replayed_tables == tables


def test_applied_migration_file_deletion_is_detected(tmp_path: Path):
    player = MigrationPlayer(f"sqlite:///{tmp_path / 'deletion.db'}", tmp_path)
    player.init_and_configure()
    migration_dir = tmp_path / "migrations" / "primary"
    migration_dir.mkdir(parents=True, exist_ok=True)
    migration = migration_dir / "primary__0001_deleted.sql"
    migration.write_text(
        "-- upgrade\nCREATE TABLE deleted (id INTEGER PRIMARY KEY);\n"
        "-- rollback\nDROP TABLE deleted;\n",
        encoding="utf-8",
    )
    player.migrate()
    migration.unlink()

    with pytest.raises(AssertionError, match="missing files"):
        player.assert_history_integrity()


def test_staged_schema_upgrade_rollback_and_reapply_converges(tmp_path: Path):
    database = tmp_path / "staged.db"
    player = MigrationPlayer(f"sqlite:///{database}", tmp_path)
    player.init_and_configure()
    migration_dir = tmp_path / "migrations" / "primary"
    migration_dir.mkdir(parents=True, exist_ok=True)
    migrations = {
        1: (
            "CREATE TABLE accounts (id INTEGER PRIMARY KEY);",
            "DROP TABLE accounts;",
        ),
        2: (
            "ALTER TABLE accounts ADD COLUMN email TEXT;",
            "ALTER TABLE accounts DROP COLUMN email;",
        ),
        3: (
            "CREATE INDEX ix_accounts_email ON accounts (email);",
            "DROP INDEX ix_accounts_email;",
        ),
    }
    for number, (upgrade, rollback) in migrations.items():
        (migration_dir / f"primary__{number:04d}_stage.sql").write_text(
            f"-- upgrade\n{upgrade}\n-- rollback\n{rollback}\n",
            encoding="utf-8",
        )

    player.migrate()
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("PRAGMA table_info(accounts)").fetchall()[1][1] == "email"
        assert connection.execute("PRAGMA index_list(accounts)").fetchall()

    player.rollback(2)
    with closing(sqlite3.connect(database)) as connection:
        assert not connection.execute("PRAGMA index_list(accounts)").fetchall()
        assert [row[1] for row in connection.execute("PRAGMA table_info(accounts)")] == ["id"]

    player.rollback()
    with closing(sqlite3.connect(database)) as connection:
        assert not connection.execute("SELECT name FROM sqlite_master WHERE name = 'accounts'").fetchall()

    player.migrate()
    player.assert_converged()


def test_failed_migration_can_be_repaired_and_replayed(tmp_path: Path):
    database = tmp_path / "recovery.db"
    player = MigrationPlayer(f"sqlite:///{database}", tmp_path)
    player.init_and_configure()
    migration_dir = tmp_path / "migrations" / "primary"
    migration_dir.mkdir(parents=True, exist_ok=True)
    (migration_dir / "primary__0001_initial.sql").write_text(
        "-- upgrade\nCREATE TABLE users (id INTEGER PRIMARY KEY);\n"
        "-- rollback\nDROP TABLE users;\n",
        encoding="utf-8",
    )
    player.migrate()
    migration = migration_dir / "primary__0002_recovery.sql"
    migration.write_text(
        "-- upgrade\nCREATE TABLE profiles (id INTEGER PRIMARY KEY);\n"
        "INVALID SQL;\n-- rollback\nDROP TABLE profiles;\n",
        encoding="utf-8",
    )

    failed = player.cli.run("migrate", check=False)
    assert failed.returncode != 0
    assert "0002" in player.cli.run("status").plain_output

    migration.write_text(
        "-- upgrade\nCREATE TABLE profiles (id INTEGER PRIMARY KEY);\n"
        "-- rollback\nDROP TABLE profiles;\n",
        encoding="utf-8",
    )
    assert player.migrate().returncode == 0
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'profiles'"
        ).fetchone()
