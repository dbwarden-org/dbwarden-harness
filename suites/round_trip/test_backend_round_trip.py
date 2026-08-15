from pathlib import Path

import pytest

from infrastructure.providers import provider_for
from schemas.registry import discover_schemas
from tools.migration_player import MigrationPlayer
from tools.schema_runner import SchemaRunner


@pytest.mark.integration
@pytest.mark.parametrize(
    ("backend", "version", "schema_name"),
    (
        ("postgres", "17", "ecommerce"),
        ("mysql", "8.4", "ecommerce"),
        ("mariadb", "11.4", "ecommerce"),
        ("clickhouse", "26.6", "analytics"),
    ),
)
def test_latest_backend_round_trip(backend: str, version: str, schema_name: str, tmp_path: Path):
    schema = next(schema for schema in discover_schemas() if schema.name == schema_name)
    provider = provider_for(backend, version)
    try:
        database_url = provider.start()
        player = MigrationPlayer(database_url, tmp_path)
        database_type = "postgresql" if backend == "postgres" else backend
        runner = SchemaRunner(schema, player, database_type=database_type)
        runner.initialize()
        runner.make_and_apply(f"{schema_name} {backend} round trip")
        assert player.status().returncode == 0
        snapshot = runner.capture_schema()
        if backend == "clickhouse":
            options = dict(snapshot.table_options["events"])
            assert options["engine"] == "MergeTree"
            assert "occurred_at" in options["sorting_key"]
        else:
            assert ("order_id", "orders", "id") in snapshot.foreign_keys["order_items"]
            assert ("user_id", "users", "id") in snapshot.foreign_keys["orders"]
            assert snapshot.unique_constraints["users"]
    finally:
        provider.stop()
