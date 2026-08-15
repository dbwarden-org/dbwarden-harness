from pathlib import Path

import pytest

from harness.matrix import DEFAULT_MATRIX, provider_versions
from infrastructure.providers import provider_for
from schemas.registry import discover_schemas
from tools.migration_player import MigrationPlayer
from tools.schema_runner import SchemaRunner


def _schema_for(backend: str):
    name = "analytics" if backend == "clickhouse" else "ecommerce"
    return next(schema for schema in discover_schemas() if schema.name == name)


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.parametrize("backend,version", tuple(provider_versions(DEFAULT_MATRIX)))
def test_declared_database_versions_complete_a_round_trip(
    backend: str, version: str, tmp_path: Path
):
    schema = _schema_for(backend)
    provider = provider_for(backend, version)
    try:
        database_url = provider.start()
        player = MigrationPlayer(database_url, tmp_path)
        database_type = "postgresql" if backend == "postgres" else backend
        runner = SchemaRunner(schema, player, database_type=database_type)
        runner.initialize()
        runner.make_and_apply(f"{schema.name} {backend} {version} round trip")
        player.assert_converged()
    finally:
        provider.stop()
