"""Column modifiers, skip indexes and projections must be rendered faithfully.

Three related contracts:

* every argument a builder accepts must reach the DDL (``skip_index(expr=...)``
  is accepted and discarded);
* mutually exclusive modifiers must be refused, not concatenated
  (``DEFAULT 1 MATERIALIZED id*2`` is emitted and rejected by the server);
* index and projection *names* must be quoted the way column names already are.
"""
from __future__ import annotations

import re

import pytest

from tools.case_runner import GenerationCase
from tools.model_source import ClickHouseTable, Column_

pytestmark = pytest.mark.integration

BASE = ClickHouseTable(
    columns=(
        Column_("id", primary_key=True),
        Column_("a"),
        Column_("s", "String"),
        Column_("ts", "DateTime"),
    )
)


def _field(spec: str, column: str = "a") -> ClickHouseTable:
    return BASE.with_(column_meta={column: spec})


# Modifier pairs ClickHouse does not allow on one column.
EXCLUSIVE_PAIRS = {
    "default_and_materialized": 'default_expression="1", materialized="id*2"',
    "default_and_ephemeral": 'default_expression="1", ephemeral="0"',
    "alias_and_codec": 'alias="id+1", codec="ZSTD(3)"',
}


@pytest.mark.parametrize("name", sorted(EXCLUSIVE_PAIRS))
def test_mutually_exclusive_modifiers_are_refused(clickhouse_runner, name):
    result = clickhouse_runner.run(
        GenerationCase(f"exclusive_{name}", "clickhouse", (_field(EXCLUSIVE_PAIRS[name]).source(),))
    )
    assert result.verdict() != "server-rejected", (
        f"ch.field({EXCLUSIVE_PAIRS[name]}) emitted both modifiers on one column; "
        "dbwarden should reject the combination rather than let the server do it:\n"
        f"  {result.steps[0].upgrade}\n  {result.steps[0].server_error}"
    )


# Wrapper flags that a raw ``type=`` override must not silently cancel.
WRAPPERS = {
    "low_cardinality": ('type="String", low_cardinality=True', "LowCardinality"),
    "nullable": ('type="String", nullable=True', "Nullable"),
}


@pytest.mark.parametrize("name", sorted(WRAPPERS))
def test_type_override_does_not_cancel_wrapper_flags(clickhouse_runner, name):
    spec, expected = WRAPPERS[name]
    result = clickhouse_runner.run(
        GenerationCase(f"wrapper_{name}", "clickhouse", (_field(spec).source(),), apply=False)
    )
    emitted = re.search(r"^\s+a (.+?),?$", result.steps[0].upgrade, re.MULTILINE)
    assert emitted and expected in emitted.group(1), (
        f"ch.field({spec}) dropped {expected}(...) - a raw type override silently "
        f"discards the wrapper flags. Emitted: {emitted.group(1) if emitted else '(none)'}"
    )


def test_codec_is_validated_against_the_column_type(clickhouse_runner):
    result = clickhouse_runner.run(
        GenerationCase("codec_mismatch", "clickhouse", (_field('codec="FPC"').source(),))
    )
    assert result.verdict() != "server-rejected", (
        "a float-only codec was emitted for an Int32 column; dbwarden should refuse "
        f"it:\n  {result.steps[0].server_error}"
    )


def test_low_cardinality_is_refused_on_numeric_columns(clickhouse_runner):
    result = clickhouse_runner.run(
        GenerationCase("lowcard_numeric", "clickhouse", (_field("low_cardinality=True").source(),))
    )
    assert result.verdict() != "server-rejected", (
        "LowCardinality was applied to a numeric column, which ClickHouse refuses by "
        f"default:\n  {result.steps[0].server_error}"
    )


def test_skip_index_expression_is_rendered(clickhouse_runner):
    table = BASE.with_(indexes='[skip_index("ix",["a"],"minmax", expr="a * 2")]')
    result = clickhouse_runner.run(
        GenerationCase("index_expr", "clickhouse", (table.source(),), apply=False)
    )
    assert "a * 2" in result.steps[0].upgrade, (
        "skip_index(expr=...) is accepted by the public API and never reaches the "
        f"DDL:\n{result.steps[0].upgrade}"
    )


def test_skip_index_requires_an_explicit_type(clickhouse_runner):
    table = BASE.with_(indexes='[skip_index("ix",["a"],"")]')
    result = clickhouse_runner.run(
        GenerationCase("index_empty_type", "clickhouse", (table.source(),), apply=False)
    )
    assert not result.steps[0].generated or "TYPE minmax" not in result.steps[0].upgrade, (
        "an empty index type was silently replaced with 'minmax'; a missing type "
        f"should be an error:\n{result.steps[0].upgrade}"
    )


QUOTED_NAMES = {
    "index_with_space": ('indexes', 'skip_index("ix ok",["a"],"minmax")'),
    "index_reserved": ('indexes', 'skip_index("index",["a"],"minmax")'),
    "projection_with_space": ('projections', 'projection("p 1","SELECT a ORDER BY a")'),
    "projection_reserved": ('projections', 'projection("order","SELECT a ORDER BY a")'),
}


@pytest.mark.parametrize("name", sorted(QUOTED_NAMES))
def test_index_and_projection_names_are_quoted(clickhouse_runner, name):
    attribute, spec = QUOTED_NAMES[name]
    table = BASE.with_(**{attribute: f"[{spec}]"})
    result = clickhouse_runner.run(
        GenerationCase(f"name_{name}", "clickhouse", (table.source(),), apply=False)
    )
    upgrade = result.steps[0].upgrade
    identifier = re.search(r"(?:ADD INDEX IF NOT EXISTS|PROJECTION) (\S+)", upgrade)
    assert identifier and identifier.group(1).startswith("`"), (
        "index and projection names are not backquoted, although column names are:\n"
        f"{upgrade}"
    )


def test_negative_index_granularity_is_refused(clickhouse_runner):
    table = BASE.with_(indexes='[skip_index("ix",["a"],"minmax", granularity=-1)]')
    result = clickhouse_runner.run(
        GenerationCase("index_negative_granularity", "clickhouse", (table.source(),))
    )
    assert result.verdict() != "server-rejected", (
        "a negative GRANULARITY was passed straight through to the server:\n"
        f"  {result.steps[0].server_error}"
    )
