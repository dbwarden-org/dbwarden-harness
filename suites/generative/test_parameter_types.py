"""A wrong value in a builder parameter must be reported, not absorbed.

The ClickHouse builders are typed but unenforced.  Passing a plausible-but-wrong
value -- a tuple where a list is expected, an ``int`` where a string is, an empty
string, a ``None`` -- produces one of three outcomes, and all three are silent:

* **vanish**  the table or view disappears from discovery and ``make-migrations``
  exits 0 saying there are no models;
* **leak**    a Python ``repr()`` (``['ver']``, ``None``, ``True``) is
  concatenated into the DDL;
* **drop**    the clause is omitted, or replaced with a default the user did not
  ask for -- including a different *engine*, which cannot be changed later.

The parametrisation is deliberately made of realistic mistakes: a codec wrapped
in a list, a port passed as a string, a boolean transcribed from YAML as
``"yes"``.  Each test asserts the contract "if dbwarden cannot honour this
value, it must say so", and reports which of the three outcomes occurred.
"""
from __future__ import annotations

import pytest

from tools.case_runner import GenerationCase
from tools.generation_probe import GenerationProbe
from tools.model_source import ClickHouseTable, Column_, module

pytestmark = pytest.mark.integration

COLUMNS = (Column_("id", primary_key=True), Column_("ts", "DateTime"), Column_("a"))
BASE = ClickHouseTable(columns=COLUMNS)


def _assert_reported(result, description: str) -> None:
    """A value dbwarden cannot honour must produce an error, not silence."""
    step = result.steps[0]

    if step.returncode != 0:
        return  # reported loudly - the contract is met.

    if not step.sql:
        swallowed = GenerationProbe(result.work_dir).swallowed_errors("make-migrations", "probe")
        detail = "\n".join(f"    {error}" for error in swallowed) or "    (probe found none)"
        pytest.fail(
            f"{description} made the object vanish: exit 0, no migration, "
            f"{'no tables found' if step.reported_no_tables else 'no changes reported'}.\n"
            f"Discarded during discovery:\n{detail}"
        )

    if result.verdict() == "server-rejected":
        pytest.fail(
            f"{description} was concatenated into the DDL and the server rejected it:\n"
            f"  {step.upgrade[:300]}\n  {step.server_error}"
        )


# --- ch_table() -------------------------------------------------------------

TABLE_PARAMS = {
    "order_by_int": {"order_by": "1"},
    "order_by_dict": {"order_by": '{"id": 1}'},
    "order_by_nested": {"order_by": '[["id"]]'},
    "order_by_empty_string": {"order_by": '""'},
    "order_by_whitespace": {"order_by": '"  "'},
    "order_by_duplicate": {"order_by": '["id","id"]'},
    "primary_key_int": {"primary_key": "1"},
    "primary_key_empty": {"primary_key": "[]"},
    "primary_key_duplicate": {"primary_key": '["id","id"]'},
    "partition_by_list": {"partition_by": '["toYYYYMM(ts)"]'},
    "partition_by_int": {"partition_by": "1"},
    "partition_by_tuple": {"partition_by": '("a","ts")'},
    "partition_by_empty": {"partition_by": '""'},
    "sample_by_list": {"sample_by": '["id"]'},
    "sample_by_int": {"sample_by": "1"},
    "sample_by_empty": {"sample_by": '""'},
    "ttl_tuple": {"ttl": '("ts + toIntervalDay(1)",)'},
    "ttl_int": {"ttl": "1"},
    "ttl_empty_member": {"ttl": '[""]'},
    "ttl_none_member": {"ttl": "[None]"},
    "settings_list": {"settings": '[("index_granularity","4096")]'},
    "settings_none_value": {"settings": '{"index_granularity": None}'},
    "settings_nested": {"settings": '{"a": {"b": "c"}}'},
    "settings_int_key": {"settings": '{1: "x"}'},
    "indexes_unwrapped": {"indexes": 'skip_index("ix",["a"],"minmax")'},
    "indexes_none_member": {"indexes": "[None]"},
    "projections_unwrapped": {"projections": 'projection("p","SELECT a ORDER BY a")'},
    "projections_none_member": {"projections": "[None]"},
    "engine_none": {"engine": "None"},
    "engine_empty": {"engine": '""'},
    "engine_lowercase": {"engine": '"mergetree"'},
    "zookeeper_path_only": {"zookeeper_path": '"/ch/t"'},
    "replica_name_only": {"replica_name": '"{replica}"'},
}


@pytest.mark.parametrize("name", sorted(TABLE_PARAMS))
def test_ch_table_parameter_is_honoured_or_reported(clickhouse_runner, name):
    table = BASE.with_(**TABLE_PARAMS[name])
    result = clickhouse_runner.run(
        GenerationCase(f"param_{name}", "clickhouse", (table.source(),))
    )
    _assert_reported(result, f"ch_table({name.replace('_', ' ')})")


ENGINE_DEFAULTING = {
    "engine_none": "None",
    "engine_empty": '""',
}


@pytest.mark.parametrize("name", sorted(ENGINE_DEFAULTING))
def test_missing_engine_does_not_silently_become_mergetree(clickhouse_runner, name):
    """The engine cannot be changed later, so a silent fallback is unrecoverable."""
    table = BASE.with_(engine=ENGINE_DEFAULTING[name])
    result = clickhouse_runner.run(
        GenerationCase(f"engine_default_{name}", "clickhouse", (table.source(),), apply=False)
    )
    if result.steps[0].returncode != 0:
        return
    assert "MergeTree" not in result.steps[0].upgrade, (
        f"{name} silently produced ENGINE = MergeTree(). Because an engine change "
        "cannot be migrated afterwards, a typo'd engine name is unrecoverable "
        "without rebuilding the table."
    )


# --- ch.field() -------------------------------------------------------------

FIELD_PARAMS = {
    "codec_list": 'codec=["ZSTD(3)"]',
    "codec_int": "codec=1",
    "codec_empty": 'codec=""',
    "codec_whitespace": 'codec="  "',
    "type_int": "type=1",
    "type_list": 'type=["String"]',
    "type_empty": 'type=""',
    "type_whitespace": 'type="  "',
    "ttl_list": 'ttl=["ts + toIntervalDay(1)"]',
    "ttl_int": "ttl=1",
    "ttl_empty": 'ttl=""',
    "materialized_empty": 'materialized=""',
    "alias_empty": 'alias=""',
    "ephemeral_empty": 'ephemeral=""',
    "default_empty": 'default_expression=""',
    "low_cardinality_string": 'low_cardinality="yes"',
    "low_cardinality_int": "low_cardinality=1",
    "nullable_string": 'nullable="yes"',
    "nullable_int": "nullable=1",
}

# Modifiers whose value must survive into the DDL if it is accepted at all.
MUST_NOT_VANISH = {
    "codec_list": "CODEC",
    "codec_int": "CODEC",
    "ttl_empty": "TTL",
    "materialized_empty": "MATERIALIZED",
    "alias_empty": "ALIAS",
    "ephemeral_empty": "EPHEMERAL",
    "default_empty": "DEFAULT",
}


@pytest.mark.parametrize("name", sorted(FIELD_PARAMS))
def test_ch_field_parameter_is_honoured_or_reported(clickhouse_runner, name):
    table = BASE.with_(column_meta={"a": FIELD_PARAMS[name]})
    result = clickhouse_runner.run(
        GenerationCase(f"field_{name}", "clickhouse", (table.source(),))
    )
    _assert_reported(result, f"ch.field({FIELD_PARAMS[name]})")

    keyword = MUST_NOT_VANISH.get(name)
    if keyword and result.steps[0].generated:
        emitted = next(
            (line for line in result.steps[0].upgrade.splitlines() if line.strip().startswith("a ")),
            "",
        )
        assert keyword in emitted, (
            f"ch.field({FIELD_PARAMS[name]}) was accepted and then discarded; the "
            f"column renders as if the modifier were never written: {emitted.strip()!r}"
        )


# --- engines ----------------------------------------------------------------

ENGINE_ARGS = {
    "replacing_int": "replacing_merge_tree(1)",
    "replacing_list": 'replacing_merge_tree(["ver"])',
    "replacing_empty": 'replacing_merge_tree("")',
    "summing_int": "summing_merge_tree(1)",
    "summing_empty": 'summing_merge_tree("")',
    "collapsing_int": "collapsing_merge_tree(1)",
    "graphite_empty": 'graphite_merge_tree("")',
    "replicated_empty": 'replicated_merge_tree("", "")',
    "replicated_none": "replicated_merge_tree(None, None)",
    "distributed_empty": 'distributed(cluster="", database="", table="")',
    "buffer_negative": 'buffer("d","t",-1,-1,-1,-1,-1,-1,-1)',
    "buffer_strings": 'buffer("d","t","a","b","c","d","e","f","g")',
    "join_bad_strictness": 'join_engine("BOGUS","NOPE","id")',
    "join_no_keys": 'join_engine("ANY","LEFT")',
    "url_empty": 'url_engine("", "")',
    "file_empty": 'file_engine("")',
    "dictionary_engine_empty": 'dictionary_engine("")',
    "merge_empty": 'merge("", "")',
    "mysql_negative_port": 'mysql_engine("h", -1, "db", "t", "u", "p")',
    "mysql_string_port": 'mysql_engine("h", "3306", "db", "t", "u", "p")',
}

# Empty/None arguments that silently select a *different* engine semantic.
SEMANTIC_CHANGE = {
    "replacing_empty": ("ReplacingMergeTree", "deduplicates by insertion order, not by version column"),
    "summing_empty": ("SummingMergeTree", "sums every numeric column, not the named one"),
    "replicated_none": ("ReplicatedMergeTree", "falls back to the implicit-path form"),
}


@pytest.mark.parametrize("name", sorted(ENGINE_ARGS))
def test_engine_arguments_are_validated(clickhouse_runner, name):
    columns = COLUMNS + (Column_("ver"), Column_("sign", "SmallInteger"), Column_("v", "Float"))
    ordered = not name.startswith(("buffer", "join", "url", "file", "dictionary_engine", "merge_", "distributed", "mysql"))
    table = ClickHouseTable(
        columns=columns,
        engine=ENGINE_ARGS[name],
        order_by='["id"]' if ordered else None,
    )
    result = clickhouse_runner.run(
        GenerationCase(f"engine_arg_{name}", "clickhouse", (table.source(),))
    )
    _assert_reported(result, f"{ENGINE_ARGS[name]}")


@pytest.mark.parametrize("name", sorted(SEMANTIC_CHANGE))
def test_empty_engine_argument_does_not_change_engine_semantics(clickhouse_runner, name):
    engine, consequence = SEMANTIC_CHANGE[name]
    columns = COLUMNS + (Column_("ver"), Column_("v", "Float"))
    table = ClickHouseTable(columns=columns, engine=ENGINE_ARGS[name], order_by='["id"]')
    result = clickhouse_runner.run(
        GenerationCase(f"engine_semantic_{name}", "clickhouse", (table.source(),), apply=False)
    )
    if result.steps[0].returncode != 0:
        return
    assert f"{engine}()" not in result.steps[0].upgrade, (
        f"{ENGINE_ARGS[name]} silently produced a bare {engine}(), which "
        f"{consequence}. That is a wrong-results bug rather than an error."
    )
