from pathlib import Path

from schemas.registry import discover_schemas
from tools.migration_player import MigrationPlayer
from tools.schema_runner import SchemaRunner


def test_ecommerce_schema_runs_through_the_public_cli(tmp_path: Path):
    schema = next(schema for schema in discover_schemas() if schema.name == "ecommerce")
    player = MigrationPlayer(f"sqlite:///{tmp_path / 'app.db'}", tmp_path)
    runner = SchemaRunner(schema, player, database_type="sqlite")

    config = runner.initialize()

    assert config.exists()
    assert "app" in config.read_text(encoding="utf-8")
