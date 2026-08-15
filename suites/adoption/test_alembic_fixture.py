import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from tools.migration_player import MigrationPlayer


def test_alembic_adoption_fixture_documents_public_handoff():
    fixture = Path(__file__).parent / "fixtures" / "alembic" / "README.md"
    text = fixture.read_text(encoding="utf-8")
    assert "generate-models" in text
    assert "baseline" in text


def test_existing_sqlite_schema_can_be_reverse_engineered(tmp_path: Path):
    database = tmp_path / "alembic.db"
    with closing(sqlite3.connect(database)) as connection:
        connection.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR(255) NOT NULL UNIQUE)"
        )

    player = MigrationPlayer(f"sqlite:///{database}", tmp_path)
    player.init_and_configure()
    result = player.generate_models("--output", "generated", "--single-file")

    assert result.returncode == 0
    generated = tmp_path / "generated" / "models.py"
    assert generated.exists()
    assert "users" in generated.read_text(encoding="utf-8")


@pytest.mark.parametrize("handoff", ("alembic", "django", "atlas"))
def test_existing_schema_can_be_baselined_without_reapplying_ddl(tmp_path: Path, handoff: str):
    database = tmp_path / f"{handoff}-baseline.db"
    with closing(sqlite3.connect(database)) as connection:
        connection.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR(255) NOT NULL UNIQUE)"
        )

    player = MigrationPlayer(f"sqlite:///{database}", tmp_path)
    player.init_and_configure()
    migration_dir = tmp_path / "migrations" / "primary"
    migration_dir.mkdir(parents=True, exist_ok=True)
    (migration_dir / f"primary__0001_{handoff}_baseline.sql").write_text(
        f"-- upgrade\n-- Existing {handoff} schema baseline.\n"
        "-- rollback\n-- Baseline rollback is intentionally empty.\n",
        encoding="utf-8",
    )

    result = player.cli.run("migrate", "--baseline", "--to-version", "0001")

    assert result.returncode == 0
    assert "0001" in player.cli.run("history").plain_output


def test_adoption_fixture_documents_all_supported_handoffs():
    root = Path(__file__).parent / "fixtures"
    for name in ("alembic", "django", "atlas"):
        text = (root / name / "README.md").read_text(encoding="utf-8").lower()
        assert "baseline" in text
        assert "schema" in text
