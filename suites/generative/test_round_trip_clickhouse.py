"""Reverse engineering must produce models that reproduce the same database.

``suites/round_trip`` proves a schema survives migrate + inspect.  This suite
closes the loop the way an adopting user does: generate models from a live
database, commit them, and run ``make-migrations`` again.  A converged tool
produces nothing.  Anything else is drift that only shows up after the generated
models are already in the repository.
"""
from __future__ import annotations

import pytest

from tools.model_source import ClickHouseTable, Column_

pytestmark = pytest.mark.integration

ID = Column_("id", primary_key=True)

SHAPES: dict[str, ClickHouseTable] = {
    "plain": ClickHouseTable(columns=(ID, Column_("a", "String"))),
    "codec": ClickHouseTable(
        columns=(ID, Column_("a", "String")),
        column_meta={"a": 'codec="ZSTD(3)", low_cardinality=True'},
    ),
    "nullable": ClickHouseTable(
        columns=(ID, Column_("a", "String")), column_meta={"a": "nullable=True"}
    ),
    "default": ClickHouseTable(column_meta={"a": 'default_expression="42"'}),
    "materialized": ClickHouseTable(column_meta={"a": 'materialized="id*2"'}),
    "partition_ttl": ClickHouseTable(
        columns=(ID, Column_("ts", "DateTime")),
        partition_by='"toYYYYMM(ts)"',
        ttl='["ts + toIntervalDay(30)"]',
    ),
    "skip_index": ClickHouseTable(
        indexes='[skip_index("ix",["a"],"minmax", granularity=3)]'
    ),
    "projection": ClickHouseTable(
        projections='[projection("p","SELECT a, count() GROUP BY a")]'
    ),
    "replacing": ClickHouseTable(
        columns=(ID, Column_("ver")), engine='replacing_merge_tree("ver")'
    ),
    "summing": ClickHouseTable(
        columns=(ID, Column_("v", "Float")), engine='summing_merge_tree("v")'
    ),
    "settings": ClickHouseTable(settings='{"index_granularity":"4096"}'),
    "comment": ClickHouseTable(comment="tbl", column_comments={"a": "col"}),
    "map_type": ClickHouseTable(
        columns=(ID, Column_("a", "String")),
        column_meta={"a": 'type="Map(String, Int64)"'},
    ),
}


def _run(driver, shape):
    result = driver.run(shape, SHAPES[shape].source())
    assert result.setup_ok, (
        "the round trip never got off the ground, so the assertions below would "
        f"pass vacuously:\n{result.summary()}"
    )
    return result


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_generated_models_are_importable(clickhouse_round_trip, shape):
    result = _run(clickhouse_round_trip, shape)
    broken = result.unimportable()
    assert not broken, (
        f"generate-models produced a module Python cannot load for shape {shape!r}: "
        f"{broken}"
    )


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_round_trip_converges(clickhouse_round_trip, shape):
    result = _run(clickhouse_round_trip, shape)
    assert result.converged, result.summary()


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_bookkeeping_tables_are_not_reverse_engineered(clickhouse_round_trip, shape):
    """dbwarden's own lock and history tables must never become user models."""
    result = _run(clickhouse_round_trip, shape)
    assert not result.bookkeeping_models, (
        "generate-models turned dbwarden's own bookkeeping tables into user models "
        f"({list(result.bookkeeping_models)}). The next make-migrations then manages "
        "them as user tables, and its rollback drops the migration history:\n"
        f"{result.remake_sql[:800]}"
    )


def test_diff_and_make_migrations_agree_after_reverse_engineering(clickhouse_round_trip):
    """The two commands must not disagree about whether work is pending."""
    disagreements = []
    for shape in SHAPES:
        result = _run(clickhouse_round_trip, shape)
        if result.diff_is_clean and result.regenerated_migration:
            disagreements.append(
                f"  {shape}: diff reports no differences but make-migrations wrote a file"
            )
    assert not disagreements, (
        "dbwarden diff and dbwarden make-migrations reached opposite conclusions "
        "about the same models and database:\n" + "\n".join(disagreements)
    )
