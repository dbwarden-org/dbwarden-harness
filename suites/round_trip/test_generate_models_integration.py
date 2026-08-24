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


@pytest.mark.integration
def test_clickhouse_native_types_round_trip(tmp_path: Path):
    schema = next(schema for schema in discover_schemas() if schema.name == "analytics_types")
    provider = provider_for("clickhouse", "26.6")
    try:
        player = MigrationPlayer(provider.start(), tmp_path)
        runner = SchemaRunner(schema, player, database_type="clickhouse")
        runner.initialize()
        runner.make_and_apply("analytics_types native types round trip")

        generated = runner.reverse_engineer(
            exclude_tables="_dbwarden_migrations,_dbwarden_seeds,dbwarden_lock",
            clickhouse_engines=True,
            relationships=False,
        )
        source = _assert_generated_model(generated, schema.expected_tables)
        assert "DateTime64(3)" in source
        assert "Enum8(" in source
        assert "FixedString(16)" in source
        assert "UUID" in source

        player.configure(
            database_name=schema.name,
            model_paths=("generated",),
            database_type="clickhouse",
        )
        player.assert_converged()
    finally:
        provider.stop()


@pytest.mark.integration
def test_postgresql_identity_and_index_sort_round_trip(tmp_path: Path):
    schema = next(schema for schema in discover_schemas() if schema.name == "ecommerce_advanced")
    provider = provider_for("postgres", "17")
    try:
        player = MigrationPlayer(provider.start(), tmp_path)
        runner = SchemaRunner(schema, player, database_type="postgresql")
        runner.initialize()
        runner.make_and_apply("ecommerce_advanced identity and index sort round trip")

        generated = runner.reverse_engineer(
            exclude_tables="_dbwarden_migrations,_dbwarden_seeds,dbwarden_lock",
            relationships=False,
        )
        source = _assert_generated_model(generated, schema.expected_tables)
        assert "identity=" in source
        assert "column_sorting" in source
        assert "DESC NULLS LAST" in source

        player.configure(
            database_name=schema.name,
            model_paths=("generated",),
            database_type="postgresql",
        )
        player.assert_converged()
    finally:
        provider.stop()


@pytest.mark.integration
def test_postgresql_generated_identity_params_and_exclusion_round_trip(tmp_path: Path):
    schema = next(schema for schema in discover_schemas() if schema.name == "ecommerce_pg_features")
    provider = provider_for("postgres", "17")
    try:
        player = MigrationPlayer(provider.start(), tmp_path)
        runner = SchemaRunner(schema, player, database_type="postgresql")
        runner.initialize()
        runner.make_and_apply("ecommerce_pg_features generated identity exclusion round trip")

        generated = runner.reverse_engineer(
            exclude_tables="_dbwarden_migrations,_dbwarden_seeds,dbwarden_lock",
            relationships=False,
        )
        source = _assert_generated_model(generated, schema.expected_tables)
        assert "identity_start=" in source
        assert "identity_increment=" in source
        assert "generated=" in source
        assert "pg_excludes" in source
        assert "EXCLUDE" in source

        player.configure(
            database_name=schema.name,
            model_paths=("generated",),
            database_type="postgresql",
        )
        player.assert_converged()
    finally:
        provider.stop()


@pytest.mark.integration
def test_clickhouse_mode_b_materialized_view_round_trip(tmp_path: Path):
    schema = next(schema for schema in discover_schemas() if schema.name == "analytics_mv")
    provider = provider_for("clickhouse", "26.6")
    try:
        player = MigrationPlayer(provider.start(), tmp_path)
        runner = SchemaRunner(schema, player, database_type="clickhouse")
        runner.initialize()
        runner.make_and_apply("analytics_mv Mode B round trip")

        generated = runner.reverse_engineer(
            exclude_tables="_dbwarden_migrations,_dbwarden_seeds,dbwarden_lock",
            clickhouse_engines=True,
            relationships=False,
        )
        source = _assert_generated_model(generated, schema.expected_tables)
        assert "class EventSummariesMv(MaterializedView)" in source
        assert "materialized_view(" in source
        assert "to='event_summaries'" in source
        assert "comment = 'Analytics events'" in source

        player.configure(
            database_name=schema.name,
            model_paths=("generated",),
            database_type="clickhouse",
        )
        player.assert_converged()
    finally:
        provider.stop()


@pytest.mark.integration
def test_clickhouse_mode_a_materialized_view_round_trip(tmp_path: Path):
    schema = next(schema for schema in discover_schemas() if schema.name == "analytics_full")
    provider = provider_for("clickhouse", "26.6")
    try:
        player = MigrationPlayer(provider.start(), tmp_path)
        runner = SchemaRunner(schema, player, database_type="clickhouse")
        runner.initialize()
        runner.make_and_apply("analytics_full Mode A round trip")

        generated = runner.reverse_engineer(
            exclude_tables="_dbwarden_migrations,_dbwarden_seeds,dbwarden_lock",
            clickhouse_engines=True,
            relationships=False,
        )
        source = _assert_generated_model(generated, schema.expected_tables)
        assert "class EventTypeStats(Base)" in source
        assert "class EventTypeStatsMv(MaterializedView)" in source
        assert "materialized_view(" in source
        assert "to='event_type_stats'" in source
        assert "comment = 'Analytics events'" in source

        player.configure(
            database_name=schema.name,
            model_paths=("generated",),
            database_type="clickhouse",
        )
        player.assert_converged()
    finally:
        provider.stop()


@pytest.mark.integration
def test_clickhouse_refreshable_materialized_view_round_trip(tmp_path: Path):
    schema = next(schema for schema in discover_schemas() if schema.name == "analytics_refreshable_mv")
    provider = provider_for("clickhouse", "26.6")
    try:
        player = MigrationPlayer(provider.start(), tmp_path)
        runner = SchemaRunner(schema, player, database_type="clickhouse")
        runner.initialize()
        runner.make_and_apply("analytics_refreshable_mv refreshable round trip")

        generated = runner.reverse_engineer(
            exclude_tables="_dbwarden_migrations,_dbwarden_seeds,dbwarden_lock",
            clickhouse_engines=True,
            relationships=False,
        )
        source = _assert_generated_model(generated, schema.expected_tables)
        assert "class EventSummariesMv(MaterializedView)" in source
        assert "materialized_view(" in source
        assert "to='event_summaries'" in source
        assert "refresh='EVERY 1 HOUR'" in source

        player.configure(
            database_name=schema.name,
            model_paths=("generated",),
            database_type="clickhouse",
        )
        player.assert_converged()
    finally:
        provider.stop()


@pytest.mark.integration
def test_clickhouse_aggregating_view_round_trip(tmp_path: Path):
    schema = next(schema for schema in discover_schemas() if schema.name == "analytics_aggregating")
    provider = provider_for("clickhouse", "26.6")
    try:
        player = MigrationPlayer(provider.start(), tmp_path)
        runner = SchemaRunner(schema, player, database_type="clickhouse")
        runner.initialize()
        runner.make_and_apply("analytics_aggregating aggregating view round trip")

        generated = runner.reverse_engineer(
            exclude_tables="_dbwarden_migrations,_dbwarden_seeds,dbwarden_lock",
            clickhouse_engines=True,
            relationships=False,
        )
        source = _assert_generated_model(generated, schema.expected_tables)
        assert "AggregatingMergeTree" in source
        assert "AggregateFunction" in source
        assert "class EventTypeStatsMv(MaterializedView)" in source
        assert "sumState" in source
        assert "countState" in source

        player.configure(
            database_name=schema.name,
            model_paths=("generated",),
            database_type="clickhouse",
        )
        player.assert_converged()
    finally:
        provider.stop()


@pytest.mark.integration
def test_clickhouse_ttl_codec_and_settings_round_trip(tmp_path: Path):
    schema = next(schema for schema in discover_schemas() if schema.name == "analytics_ttl")
    provider = provider_for("clickhouse", "26.6")
    try:
        player = MigrationPlayer(provider.start(), tmp_path)
        runner = SchemaRunner(schema, player, database_type="clickhouse")
        runner.initialize()
        runner.make_and_apply("analytics_ttl TTL codec settings round trip")

        generated = runner.reverse_engineer(
            exclude_tables="_dbwarden_migrations,_dbwarden_seeds,dbwarden_lock",
            clickhouse_engines=True,
            relationships=False,
        )
        source = _assert_generated_model(generated, schema.expected_tables)
        assert "ch_ttl" in source
        assert "toIntervalMonth(6)" in source
        assert "codec=" in source
        assert "ZSTD(5)" in source
        assert "ttl=" in source
        assert "toIntervalDay(30)" in source
        assert "ch_settings" in source
        assert "index_granularity" in source

        player.configure(
            database_name=schema.name,
            model_paths=("generated",),
            database_type="clickhouse",
        )
        player.assert_converged()
    finally:
        provider.stop()


@pytest.mark.integration
def test_postgresql_advanced_indexes_and_table_props_round_trip(tmp_path: Path):
    schema = next(schema for schema in discover_schemas() if schema.name == "ecommerce_pg_advanced")
    provider = provider_for("postgres", "17")
    try:
        player = MigrationPlayer(provider.start(), tmp_path)
        runner = SchemaRunner(schema, player, database_type="postgresql")
        runner.initialize()
        runner.make_and_apply("ecommerce_pg_advanced indexes and table props round trip")

        generated = runner.reverse_engineer(
            exclude_tables="_dbwarden_migrations,_dbwarden_seeds,dbwarden_lock",
            relationships=False,
        )
        source = _assert_generated_model(generated, schema.expected_tables)
        assert "pg_storage_params" in source
        assert "fillfactor" in source
        assert "collation=" in source
        assert "compression=" in source
        assert "deferrable=True" in source
        assert "initially='DEFERRED'" in source
        assert "no_inherit" in source
        assert "ix_orders_email_partial" in source
        assert "ix_orders_session_expr" in source
        assert "lower(session_token::text)" in source

        player.configure(
            database_name=schema.name,
            model_paths=("generated",),
            database_type="postgresql",
        )
        player.assert_converged()
    finally:
        provider.stop()


@pytest.mark.integration
def test_clickhouse_projections_and_skip_indexes_round_trip(tmp_path: Path):
    schema = next(schema for schema in discover_schemas() if schema.name == "analytics_projections")
    provider = provider_for("clickhouse", "26.6")
    try:
        player = MigrationPlayer(provider.start(), tmp_path)
        runner = SchemaRunner(schema, player, database_type="clickhouse")
        runner.initialize()
        runner.make_and_apply("analytics_projections projections and indexes round trip")

        generated = runner.reverse_engineer(
            exclude_tables="_dbwarden_migrations,_dbwarden_seeds,dbwarden_lock",
            clickhouse_engines=True,
            relationships=False,
        )
        source = _assert_generated_model(generated, schema.expected_tables)
        assert "class Events(Base)" in source
        assert "ProjectionSpec(" in source
        assert "by_name" in source
        assert "ChIndexSpec(" in source
        assert "bloom_filter" in source

        player.configure(
            database_name=schema.name,
            model_paths=("generated",),
            database_type="clickhouse",
        )
        player.assert_converged()
    finally:
        provider.stop()


@pytest.mark.integration
def test_clickhouse_materialized_view_with_join_round_trip(tmp_path: Path):
    schema = next(schema for schema in discover_schemas() if schema.name == "analytics_mv_join")
    provider = provider_for("clickhouse", "26.6")
    try:
        player = MigrationPlayer(provider.start(), tmp_path)
        runner = SchemaRunner(schema, player, database_type="clickhouse")
        runner.initialize()
        runner.make_and_apply("analytics_mv_join MV with JOIN round trip")

        generated = runner.reverse_engineer(
            exclude_tables="_dbwarden_migrations,_dbwarden_seeds,dbwarden_lock",
            clickhouse_engines=True,
            relationships=False,
        )
        source = _assert_generated_model(generated, schema.expected_tables)
        assert "class EventUserValues(Base)" in source
        assert "class EventUserValuesMv(MaterializedView)" in source
        assert "materialized_view(" in source
        assert "to='event_user_values'" in source
        mv_section = source.split("class EventUserValuesMv", 1)[1].split("\n\nclass", 1)[0]
        assert "events" in mv_section and "users" in mv_section

        player.configure(
            database_name=schema.name,
            model_paths=("generated",),
            database_type="clickhouse",
        )
        player.assert_converged()
    finally:
        provider.stop()
