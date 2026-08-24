"""The documented escape hatches for expressions must work in every position.

``ch_raw()`` exists so a user can put a ClickHouse expression where dbwarden
otherwise expects a column name, and ``aggregating_view()``'s docstring states
that expression fields "accept ``ColumnElement``, ``ChRaw``, or plain ``str``".

The failure mode here is the worst kind: a ``ChRaw`` in the wrong field does not
raise, it makes the whole table disappear from discovery, so ``make-migrations``
exits 0 saying there are no models.  These tests pin the escape hatch down in
every field that accepts an expression, and use :class:`GenerationProbe` to name
the discarded exception when one goes missing.
"""
from __future__ import annotations

import pytest

from tools.case_runner import GenerationCase
from tools.generation_probe import GenerationProbe
from tools.model_source import ClickHouseTable, Column_

pytestmark = pytest.mark.integration

COLUMNS = (Column_("id", primary_key=True), Column_("ts", "DateTime"), Column_("a"))

RAW_POSITIONS = {
    "order_by_list": {"order_by": '[ch_raw("toStartOfHour(ts)"), "id"]'},
    "order_by_scalar": {"order_by": 'ch_raw("toStartOfHour(ts)")'},
    "primary_key": {"order_by": '["id"]', "primary_key": '[ch_raw("id")]'},
    "table_ttl": {"order_by": '["id"]', "ttl": '[ch_raw("ts + toIntervalDay(1)")]'},
    "partition_by": {"order_by": '["id"]', "partition_by": 'ch_raw("toYYYYMM(ts)")'},
    "sample_by": {"order_by": '["id"]', "sample_by": 'ch_raw("id")'},
}


@pytest.mark.parametrize("position", sorted(RAW_POSITIONS))
def test_ch_raw_is_accepted_in_every_expression_field(clickhouse_runner, position):
    table = ClickHouseTable(columns=COLUMNS).with_(**RAW_POSITIONS[position])
    result = clickhouse_runner.run(
        GenerationCase(f"raw_{position}", "clickhouse", (table.source(),), apply=False)
    )
    step = result.steps[0]
    if step.generated:
        return

    swallowed = GenerationProbe(result.work_dir).swallowed_errors("make-migrations", "probe")
    detail = "\n".join(f"    {error}" for error in swallowed) or "    (probe found none)"
    pytest.fail(
        f"ch_raw() in {position} produced no migration; dbwarden reported "
        f"{'no tables found' if step.reported_no_tables else 'no changes'} and exited "
        f"{step.returncode}. The table silently vanished from discovery.\n"
        f"Discarded during discovery:\n{detail}"
    )


def test_column_element_is_accepted_where_documented(clickhouse_runner):
    """``aggregating_view`` documents ColumnElement support for expression fields."""
    table = ClickHouseTable(
        columns=COLUMNS, partition_by='func.toYYYYMM(Column("ts", DateTime))'
    )
    result = clickhouse_runner.run(
        GenerationCase("colelement_partition", "clickhouse", (table.source(),), apply=False)
    )
    assert result.steps[0].generated, (
        "a SQLAlchemy ColumnElement in partition_by was rejected, although the "
        "aggregating_view docstring states expression fields accept ColumnElement:\n"
        f"{result.steps[0].stdout[-500:]}"
    )


def test_aggregating_view_triad_can_be_declared(clickhouse_runner):
    """The documented source->target->MV rollup form must be usable."""
    source = ClickHouseTable(
        name="src",
        class_name="Src",
        columns=(Column_("id", primary_key=True), Column_("amt", "Float")),
    ).render()
    rollup = '''
class Roll(Base):
    __tablename__ = "roll"

    class Meta(CHViewMeta):
        ch = aggregating_view(source=Src, group_by=["id"],
                              aggregates=[agg.sum(Src.amt).as_("total")], order_by=["id"])
'''
    from tools.model_source import module

    result = clickhouse_runner.run(
        GenerationCase(
            "aggregating_view_triad",
            "clickhouse",
            (module("clickhouse", source, rollup),),
            apply=False,
        )
    )
    assert result.steps[0].generated, (
        "aggregating_view() is documented as generating a target table plus a "
        "matching materialized view, but the declaration cannot be loaded:\n"
        f"{result.steps[0].stdout[-500:]}"
    )
