from pathlib import Path

import pytest

from harness.cli import DbwardenCli
from harness.reference import MINIMAL_SQLITE_MODELS
from infrastructure.providers import PostgresProvider
from schemas.registry import discover_schemas
from tools.migration_player import MigrationPlayer
from tools.schema_runner import SchemaRunner


def test_sqlite_project_can_be_initialized_through_the_cli(tmp_path: Path):
    player = MigrationPlayer(f"sqlite:///{tmp_path / 'app.db'}", tmp_path)
    player.write_model_source("", filename="app/__init__.py")
    player.write_model_source(MINIMAL_SQLITE_MODELS, filename="app/models.py")
    player.init_and_configure(model_paths=("app",))
    result = DbwardenCli(tmp_path).run("config")
    assert result.returncode == 0
    assert "primary" in result.stdout.lower()


def test_sqlite_schema_round_trip_through_public_cli(tmp_path: Path):
    player = MigrationPlayer(f"sqlite:///{tmp_path / 'app.db'}", tmp_path)
    player.write_model_source("", filename="app/__init__.py")
    player.write_model_source(MINIMAL_SQLITE_MODELS, filename="app/models.py")
    player.init_and_configure(model_paths=("app",))

    migration = player.make_migrations("initial schema")
    assert migration.returncode == 0
    player.migrate()
    status = player.status()
    assert status.returncode == 0
    assert "users" in status.stdout.lower() or "applied" in status.stdout.lower()


@pytest.mark.parametrize("schema_name", ("analytics",))
def test_every_reference_schema_converges_on_sqlite(tmp_path: Path, schema_name: str):
    schema = next(schema for schema in discover_schemas() if schema.name == schema_name)
    player = MigrationPlayer(f"sqlite:///{tmp_path / f'{schema_name}.db'}", tmp_path)
    runner = SchemaRunner(schema, player, database_type="sqlite")

    runner.initialize()
    runner.make_and_apply(f"{schema_name} sqlite baseline")
    snapshot = runner.capture_schema()

    assert set(schema.expected_tables).issubset(snapshot.tables)
    assert set(schema.expected_indexes).issubset(
        {index for indexes in snapshot.indexes.values() for index in indexes}
    )


@pytest.mark.integration
def test_ecommerce_reference_schema_round_trip(tmp_path: Path):
    schema = next(schema for schema in discover_schemas() if schema.name == "ecommerce")
    with PostgresProvider() as provider:
        player = MigrationPlayer(provider.start(), tmp_path)
        runner = SchemaRunner(schema, player)

        runner.initialize()
        runner.make_and_apply("ecommerce baseline")

        assert player.status().returncode == 0
