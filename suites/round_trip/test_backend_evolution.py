from pathlib import Path

import pytest

from infrastructure.providers import provider_for
from tools.drift_checker import DriftChecker
from tools.migration_player import MigrationPlayer


def _write_migration(directory: Path, number: int, upgrade: str, rollback: str) -> None:
    (directory / f"primary__{number:04d}_evolution.sql").write_text(
        f"-- upgrade\n{upgrade}\n-- rollback\n{rollback}\n",
        encoding="utf-8",
    )


@pytest.mark.integration
@pytest.mark.parametrize("backend", ("postgres", "mysql", "mariadb"))
def test_relational_backend_evolution_rolls_back_and_reapplies(backend: str, tmp_path: Path):
    provider = provider_for(backend, {"postgres": "17", "mysql": "8.4", "mariadb": "11.4"}[backend])
    try:
        player = MigrationPlayer(provider.start(), tmp_path)
        player.init_and_configure(database_type="postgresql" if backend == "postgres" else backend)
        migration_dir = tmp_path / "migrations" / "primary"
        migration_dir.mkdir(parents=True, exist_ok=True)
        _write_migration(
            migration_dir,
            1,
            "CREATE TABLE accounts (id INTEGER NOT NULL PRIMARY KEY);",
            "DROP TABLE accounts;",
        )
        _write_migration(
            migration_dir,
            2,
            "ALTER TABLE accounts ADD COLUMN status VARCHAR(32) NOT NULL DEFAULT 'active';",
            "ALTER TABLE accounts DROP COLUMN status;",
        )

        assert player.migrate().returncode == 0
        assert "0002" in player.status().plain_output
        assert "status" in DriftChecker().capture(player.database_url).columns["accounts"]

        assert player.rollback().returncode == 0
        assert "status" not in DriftChecker().capture(player.database_url).columns["accounts"]

        assert player.migrate().returncode == 0
        assert "status" in DriftChecker().capture(player.database_url).columns["accounts"]
        player.assert_history_integrity()
    finally:
        provider.stop()


@pytest.mark.integration
def test_clickhouse_evolution_preserves_engine_metadata(tmp_path: Path):
    provider = provider_for("clickhouse", "26.6")
    try:
        player = MigrationPlayer(provider.start(), tmp_path)
        player.init_and_configure(database_type="clickhouse")
        migration_dir = tmp_path / "migrations" / "primary"
        migration_dir.mkdir(parents=True, exist_ok=True)
        _write_migration(
            migration_dir,
            1,
            "CREATE TABLE events (id Int64, occurred_at DateTime) ENGINE = MergeTree "
            "ORDER BY (occurred_at, id);",
            "DROP TABLE events;",
        )
        _write_migration(
            migration_dir,
            2,
            "ALTER TABLE events ADD COLUMN event_name String DEFAULT '';",
            "ALTER TABLE events DROP COLUMN event_name;",
        )

        assert player.migrate().returncode == 0
        snapshot = DriftChecker().capture(player.database_url)
        assert "event_name" in snapshot.columns["events"]
        options = dict(snapshot.table_options["events"])
        assert options["engine"] == "MergeTree"
        assert "occurred_at" in options["sorting_key"]

        assert player.rollback().returncode == 0
        assert "event_name" not in DriftChecker().capture(player.database_url).columns["events"]
        assert player.migrate().returncode == 0
    finally:
        provider.stop()
