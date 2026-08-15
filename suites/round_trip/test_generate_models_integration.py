from pathlib import Path

import pytest

from infrastructure.providers import provider_for
from schemas.registry import discover_schemas
from tools.migration_player import MigrationPlayer
from tools.schema_runner import SchemaRunner


def _schema_for(backend: str):
    name = "analytics" if backend == "clickhouse" else "ecommerce"
    return next(schema for schema in discover_schemas() if schema.name == name)


def _assert_generated_model(generated: Path, expected_tables: tuple[str, ...]) -> str:
    source = generated.read_text(encoding="utf-8")
    assert source.strip()
    assert "from sqlalchemy" in source
    for table in expected_tables:
        assert table in source
    return source


@pytest.mark.integration
@pytest.mark.parametrize(
    ("backend", "version"),
    (
        ("postgres", "17"),
        ("mysql", "8.4"),
        pytest.param(
            "mariadb",
            "11.4",
            marks=pytest.mark.xfail(
                reason="PyPI 0.16.5 orders MariaDB foreign-key tables incorrectly",
                strict=True,
            ),
        ),
        ("clickhouse", "26.6"),
    ),
)
def test_generate_models_reconfigures_a_real_backend(backend: str, version: str, tmp_path: Path):
    schema = _schema_for(backend)
    provider = provider_for(backend, version)
    try:
        player = MigrationPlayer(provider.start(), tmp_path)
        database_type = "postgresql" if backend == "postgres" else backend
        runner = SchemaRunner(schema, player, database_type=database_type)
        runner.initialize()
        runner.make_and_apply(f"{schema.name} {backend} generate models")

        generated = runner.reverse_engineer(
            exclude_tables="_dbwarden_migrations,_dbwarden_seeds",
            clickhouse_engines=backend == "clickhouse",
            relationships=backend != "clickhouse",
        )
        source = _assert_generated_model(generated, schema.expected_tables)
        assert "Base" in source
        assert "_dbwarden_migrations" not in source
        if backend == "clickhouse":
            assert "MergeTree" in source
            assert "ch_order_by" in source

        player.configure(
            database_name=schema.name,
            model_paths=("generated",),
            database_type=database_type,
        )
        player.assert_converged()
    finally:
        provider.stop()


def test_generate_models_supports_table_filter_on_sqlite(tmp_path: Path):
    schema = next(schema for schema in discover_schemas() if schema.name == "analytics")
    player = MigrationPlayer(f"sqlite:///{tmp_path / 'analytics.db'}", tmp_path)
    runner = SchemaRunner(schema, player, database_type="sqlite")
    runner.initialize()
    runner.make_and_apply("analytics generate models filter")

    generated = runner.reverse_engineer(output_dir="filtered", tables="events")
    source = _assert_generated_model(generated, ("events",))

    assert "events" in source
    player.configure(database_name=schema.name, model_paths=("filtered",), database_type="sqlite")
    player.assert_converged()
