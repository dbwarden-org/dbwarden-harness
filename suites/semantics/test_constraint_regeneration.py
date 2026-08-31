"""Regenerating from unchanged models must produce nothing.

The expensive failure mode here is not a broken migration, it is a confident
one. If the snapshot of a live database does not describe it exactly the way
the models do, every later `make-migrations` proposes to "fix" a schema that
was never wrong: dropping and recreating a unique constraint, rebuilding every
foreign key and index, or rewriting a column's storage. Each run applies
cleanly, so nothing fails - the schema just churns, holding locks, forever.

A release that converges once and stays converged is the contract. These tests
apply a schema, change nothing, and require silence.
"""

from pathlib import Path

import pytest

from harness.reference import CONSTRAINED_MODELS, CONSTRAINED_MODELS_RELAXED
from infrastructure.providers import provider_for
from tools.migration_player import MigrationPlayer
from tools.sql_probe import SqlProbe

CHURN_MARKERS = (
    "DROP CONSTRAINT",
    "DROP INDEX",
    "ADD CONSTRAINT",
    "CREATE INDEX",
    "ALTER COLUMN",
)


def _project(player: MigrationPlayer, database_type: str, source: str = CONSTRAINED_MODELS) -> None:
    player.write_model_source("", filename="app/__init__.py")
    player.write_model_source(source, filename="app/models.py")
    player.init_and_configure(database_type=database_type, model_paths=("app",))


def _migration_files(work_dir: Path) -> list[Path]:
    return sorted((work_dir / "migrations" / "primary").glob("*.sql"))


def _assert_no_second_migration(player: MigrationPlayer) -> None:
    before = _migration_files(player.work_dir)
    result = player.make_migrations("regenerate with no model changes")
    after = _migration_files(player.work_dir)
    added = [path for path in after if path not in before]
    if added:
        raise AssertionError(
            "Unchanged models produced a new migration:\n"
            + "\n".join(f"--- {path.name}\n{path.read_text(encoding='utf-8')}" for path in added)
            + f"\nCLI output:\n{result.plain_output}"
        )
    player.assert_converged()


def test_unchanged_models_regenerate_nothing_on_sqlite(tmp_path: Path):
    player = MigrationPlayer(f"sqlite:///{tmp_path / 'app.db'}", tmp_path)
    _project(player, "sqlite")
    player.make_migrations("constrained schema")
    player.migrate()

    _assert_no_second_migration(player)


@pytest.mark.integration
@pytest.mark.parametrize("version", ("14", "16", "17"))
def test_unchanged_models_regenerate_nothing_on_postgres(version: str, tmp_path: Path):
    """Parametrized by server version because the snapshot reads the catalog.

    Catalog columns and their defaults move between major versions. A snapshot
    query that silently returns nothing on one of them turns into constraint
    churn on exactly that version and no other.
    """
    provider = provider_for("postgres", version)
    try:
        player = MigrationPlayer(provider.start(), tmp_path)
        _project(player, "postgresql")
        player.make_migrations("constrained schema")
        player.migrate()

        _assert_no_second_migration(player)
    finally:
        provider.stop()


def test_dropping_one_constraint_leaves_the_others_alone(tmp_path: Path):
    """Removing a constraint from the models must not rewrite the whole table.

    SQLite has no ``ALTER TABLE DROP CONSTRAINT``, so it reaches this through a
    table rebuild. The rebuild is legitimate; losing the surviving check
    constraint or the table's rows during it is not.
    """
    player = MigrationPlayer(f"sqlite:///{tmp_path / 'app.db'}", tmp_path)
    _project(player, "sqlite")
    player.make_migrations("constrained schema")
    player.migrate()

    with SqlProbe(player.database_url) as probe:
        probe.execute("INSERT INTO heartbeats (branch_id, seq_no) VALUES (7, 3)")

    player.write_model_source(CONSTRAINED_MODELS_RELAXED, filename="app/models.py")
    player.make_migrations("drop the heartbeat unique constraint")
    player.migrate()

    with SqlProbe(player.database_url) as probe:
        assert probe.rows("SELECT branch_id, seq_no FROM heartbeats") == [(7, 3)], (
            "the table rebuild lost its rows"
        )
        probe.execute("INSERT INTO heartbeats (branch_id, seq_no) VALUES (7, 4)")
        probe.assert_rejects(
            "INSERT INTO heartbeats (branch_id, seq_no) VALUES (8, -1)",
            because="ck_heartbeats_seq_no was not part of the change and must survive it",
        )

    _assert_no_second_migration(player)


@pytest.mark.integration
def test_dropping_one_constraint_does_not_churn_the_rest_on_postgres(tmp_path: Path):
    provider = provider_for("postgres", "17")
    try:
        player = MigrationPlayer(provider.start(), tmp_path)
        _project(player, "postgresql")
        player.make_migrations("constrained schema")
        player.migrate()
        first = set(_migration_files(tmp_path))

        player.write_model_source(CONSTRAINED_MODELS_RELAXED, filename="app/models.py")
        player.make_migrations("drop the heartbeat unique constraint")
        added = [path for path in _migration_files(tmp_path) if path not in first]
        assert len(added) == 1, added
        sql = added[0].read_text(encoding="utf-8")
        upgrade = sql.split("-- rollback", 1)[0]

        assert "uq_heartbeats_branch_id" in upgrade, sql
        churn = [
            line.strip()
            for line in upgrade.splitlines()
            if "uq_heartbeats_branch_id" not in line
            and any(marker in line.upper() for marker in CHURN_MARKERS)
        ]
        assert not churn, (
            "dropping one constraint also rewrote unrelated objects:\n"
            + "\n".join(churn)
            + f"\n\nfull migration:\n{upgrade}"
        )

        player.migrate()
        with SqlProbe(player.database_url) as probe:
            probe.assert_rejects(
                "INSERT INTO heartbeats (branch_id, seq_no) VALUES (8, -1)",
                because="ck_heartbeats_seq_no was not part of the change and must survive it",
            )
        _assert_no_second_migration(player)
    finally:
        provider.stop()
