"""Declared constraints must reach the server and be enforced by it.

A migration that applies cleanly is not evidence that the schema constrains
anything. A release can drop every ``uniques`` and ``checks`` entry on the way
from model to SQL, apply without error, and leave a database that accepts
duplicate rows - which the application only discovers in production, usually
through an ``ON CONFLICT`` clause that has no constraint to conflict with.

These tests declare constraints, apply the migration, and then try to violate
them. The database has to refuse.
"""

from pathlib import Path

import pytest

from harness.reference import CONSTRAINED_MODELS
from infrastructure.providers import provider_for
from tools.migration_player import MigrationPlayer
from tools.sql_probe import SqlProbe

CONSTRAINT_NAMES = (
    "uq_branches_code",
    "uq_heartbeats_branch_id",
    "ck_heartbeats_seq_no",
)


def _project(player: MigrationPlayer, database_type: str) -> None:
    player.write_model_source("", filename="app/__init__.py")
    player.write_model_source(CONSTRAINED_MODELS, filename="app/models.py")
    player.init_and_configure(database_type=database_type, model_paths=("app",))


def _migration_sql(work_dir: Path) -> str:
    files = sorted((work_dir / "migrations" / "primary").glob("*.sql"))
    assert files, "dbwarden generated no migration file"
    return "\n".join(path.read_text(encoding="utf-8") for path in files)


def _assert_constraints_are_enforced(probe: SqlProbe) -> None:
    probe.execute(
        "INSERT INTO branches (code) VALUES ('north')",
        "INSERT INTO heartbeats (branch_id, seq_no) VALUES (1, 0)",
    )
    probe.assert_rejects(
        "INSERT INTO branches (code) VALUES ('north')",
        because="uq_branches_code makes branches.code unique",
    )
    probe.assert_rejects(
        "INSERT INTO heartbeats (branch_id, seq_no) VALUES (1, 5)",
        because="uq_heartbeats_branch_id makes heartbeats.branch_id unique",
    )
    probe.assert_rejects(
        "INSERT INTO heartbeats (branch_id, seq_no) VALUES (2, -1)",
        because="ck_heartbeats_seq_no requires seq_no >= 0",
    )


def test_declared_constraints_are_named_in_the_generated_sql(tmp_path: Path):
    """Fail at the artifact, before the database, so the diagnosis is legible."""
    player = MigrationPlayer(f"sqlite:///{tmp_path / 'app.db'}", tmp_path)
    _project(player, "sqlite")
    player.make_migrations("constrained schema")

    sql = _migration_sql(tmp_path)
    missing = [name for name in CONSTRAINT_NAMES if name not in sql]
    assert not missing, f"generated migration never mentions {missing}:\n{sql}"


def test_constraints_are_enforced_on_sqlite(tmp_path: Path):
    player = MigrationPlayer(f"sqlite:///{tmp_path / 'app.db'}", tmp_path)
    _project(player, "sqlite")
    player.make_migrations("constrained schema")
    player.migrate()

    with SqlProbe(player.database_url) as probe:
        _assert_constraints_are_enforced(probe)


@pytest.mark.integration
@pytest.mark.parametrize(
    ("backend", "version"),
    (
        ("postgres", "17"),
        ("postgres", "14"),
        ("mysql", "8.4"),
        ("mariadb", "11.4"),
    ),
)
def test_constraints_are_enforced_on_real_servers(backend: str, version: str, tmp_path: Path):
    provider = provider_for(backend, version)
    try:
        player = MigrationPlayer(provider.start(), tmp_path)
        _project(player, "postgresql" if backend == "postgres" else backend)
        player.make_migrations("constrained schema")
        player.migrate()

        sql = _migration_sql(tmp_path)
        assert all(name in sql for name in CONSTRAINT_NAMES), sql
        with SqlProbe(player.database_url) as probe:
            _assert_constraints_are_enforced(probe)
    finally:
        provider.stop()


@pytest.mark.integration
def test_constraints_survive_a_reverse_engineered_round_trip(tmp_path: Path):
    """`generate-models` must carry the constraints back out of the database.

    Reverse engineering that loses a constraint reports convergence while
    quietly proposing to drop it the next time the generated models are used.
    """
    provider = provider_for("postgres", "17")
    try:
        player = MigrationPlayer(provider.start(), tmp_path)
        _project(player, "postgresql")
        player.make_migrations("constrained schema")
        player.migrate()

        # dbwarden's own bookkeeping tables are not application models; the
        # supported reverse-engineering flow excludes them.
        player.generate_models(
            "--output", "generated", "--single-file",
            "--exclude-tables", "_dbwarden_migrations,_dbwarden_seeds,dbwarden_lock",
        )
        generated = (tmp_path / "generated" / "models.py").read_text(encoding="utf-8")
        assert "uq_branches_code" in generated, generated
        assert "ck_heartbeats_seq_no" in generated, generated

        player.configure(database_type="postgresql", model_paths=("generated",))
        player.assert_converged()
    finally:
        provider.stop()
