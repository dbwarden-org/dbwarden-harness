"""Expressions must be validated against the columns and types they reference.

dbwarden concatenates expression strings into the DDL and lets the server find
the problems.  That is tolerable for a genuinely free-form expression, but not
for the cases below, where the information needed to reject the model is already
in the model: a TTL cannot reference an ``ALIAS`` column, a ``Map`` key cannot be
``Nullable``, and ``DateTime64`` has a fixed scale range.
"""
from __future__ import annotations

import pytest

from tools.case_runner import GenerationCase
from tools.model_source import ClickHouseTable, Column_

pytestmark = pytest.mark.integration

BASE = (Column_("id", primary_key=True), Column_("ts", "DateTime"), Column_("a"))

UNSATISFIABLE = {
    "ttl_on_alias": ClickHouseTable(
        columns=BASE,
        ttl='["ts + toIntervalDay(1)"]',
        column_meta={"ts": 'alias="now()"'},
    ),
    "partition_on_alias": ClickHouseTable(
        columns=BASE,
        partition_by='"toYYYYMM(ts)"',
        column_meta={"ts": 'alias="now()"'},
    ),
    "datetime64_scale": ClickHouseTable(
        columns=BASE, column_meta={"a": 'type="DateTime64(12)"'}
    ),
    "map_nullable_key": ClickHouseTable(
        columns=BASE, column_meta={"a": 'type="Map(Nullable(String), Int64)"'}
    ),
}


@pytest.mark.parametrize("name", sorted(UNSATISFIABLE))
def test_unsatisfiable_expression_is_refused_before_the_server(clickhouse_runner, name):
    result = clickhouse_runner.run(
        GenerationCase(f"unsat_{name}", "clickhouse", (UNSATISFIABLE[name].source(),))
    )
    assert result.verdict() != "server-rejected", (
        "dbwarden generated DDL it had enough information to reject; the failure "
        f"surfaced from the server instead:\n  {result.steps[0].server_error}"
    )


def test_type_override_keeps_nullable_on_a_composite_type(clickhouse_runner):
    """A raw ``type=`` must not silently discard ``nullable=True``."""
    table = ClickHouseTable(
        columns=BASE, column_meta={"a": 'type="Array(Int64)", nullable=True'}
    )
    result = clickhouse_runner.run(
        GenerationCase("nullable_array", "clickhouse", (table.source(),), apply=False)
    )
    emitted = next(
        (line.strip() for line in result.steps[0].upgrade.splitlines() if line.strip().startswith("a ")),
        "",
    )
    assert "Nullable" in emitted, (
        f"nullable=True was dropped alongside a raw type override; emitted: {emitted!r}"
    )
