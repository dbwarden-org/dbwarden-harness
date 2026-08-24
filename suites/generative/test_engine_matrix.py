"""Every engine builder must produce DDL the server accepts.

``dbwarden.databases.clickhouse`` exports ~30 engine builders.  Their arguments
are rendered into the ``ENGINE = ...`` clause; none of them is quoted, so every
engine whose parameters must be SQL string literals -- replication paths, file
URIs, connection strings, table-name regexes -- produces a syntax error.  The
keyword-only integration builders have the opposite problem: their parameters
are dropped entirely and the engine is rendered with an empty argument list.

Engines that need external infrastructure (a cluster, a broker, a bucket) are
still exercised: the assertion is on the shape of the generated SQL, not on the
migration succeeding, so an "unknown cluster" is tolerated while a syntax error
or a lost parameter is not.
"""
from __future__ import annotations

import re

import pytest

from tools.case_runner import GenerationCase, report
from tools.model_source import ClickHouseTable, Column_

pytestmark = pytest.mark.integration

COLUMNS = (
    Column_("id", primary_key=True),
    Column_("ver"),
    Column_("sign", "SmallInteger"),
    Column_("val", "Float"),
    Column_("ts", "DateTime"),
)

# (case_id, engine expression, ordered?, arguments that must survive)
ENGINES: list[tuple[str, str, bool, tuple[str, ...]]] = [
    ("merge_tree", "merge_tree()", True, ()),
    ("replacing", 'replacing_merge_tree("ver")', True, ("ver",)),
    ("summing_one", 'summing_merge_tree("val")', True, ("val",)),
    ("summing_many", 'summing_merge_tree("val", "ver")', True, ("val", "ver")),
    ("aggregating", "aggregating_merge_tree()", True, ()),
    ("collapsing", 'collapsing_merge_tree("sign")', True, ("sign",)),
    ("versioned_collapsing", 'versioned_collapsing_merge_tree("sign", "ver")', True, ("sign", "ver")),
    ("graphite", 'graphite_merge_tree("graphite_rollup")', True, ("graphite_rollup",)),
    ("replicated", 'replicated_merge_tree("/clickhouse/tables/{shard}/t", "{replica}")', True,
     ("/clickhouse/tables/{shard}/t", "{replica}")),
    ("distributed", 'distributed(cluster="c", database="d", table="tt", sharding_key="rand()")', False,
     ("d", "tt")),
    ("memory", "memory()", False, ()),
    ("log", "log()", False, ()),
    ("tiny_log", "tiny_log()", False, ()),
    ("stripe_log", "stripe_log()", False, ()),
    ("null", "null()", False, ()),
    ("set", "set_engine()", False, ()),
    ("merge", 'merge("default", "^t_")', False, ("^t_",)),
    ("buffer", 'buffer("default","t",16,10,100,10000,1000000,10000000,100000000)', False, ("t",)),
    ("join", 'join_engine("ANY","LEFT","id")', False, ("id",)),
    ("url", 'url_engine("http://example.com/data.tsv", "TSV")', False,
     ("http://example.com/data.tsv", "TSV")),
    ("hdfs", 'hdfs("hdfs://nn:9000/f", "TSV")', False, ("hdfs://nn:9000/f",)),
    ("file", 'file_engine("TSV")', False, ("TSV",)),
    ("mysql", 'mysql_engine("h", 3306, "db", "tbl", "u", "pw")', False, ("db", "tbl")),
    ("postgresql", 'postgresql_engine("h", 5432, "db", "tbl", "u", "pw")', False, ("db", "tbl")),
    ("dictionary_engine", 'dictionary_engine("mydict")', False, ("mydict",)),
    ("kafka", 'kafka(broker_list="localhost:9092", topic_list="t", group_name="g", format="JSONEachRow")',
     False, ("localhost:9092", "JSONEachRow")),
    ("s3", 's3(path="https://x/y.csv", format="CSV")', False, ("https://x/y.csv", "CSV")),
    ("nats", 'nats(url="nats://h:4222", subjects="s", format="JSONEachRow")', False,
     ("nats://h:4222", "JSONEachRow")),
    ("s3_queue", 's3_queue(path="https://x/y*", format="CSV")', False, ("https://x/y*", "CSV")),
]

# Server errors that mean "this engine needs infrastructure we did not provide",
# as opposed to "dbwarden generated bad SQL".
ENVIRONMENTAL = (
    "CLUSTER_DOESNT_EXIST",
    "UNKNOWN_POLICY",
    "Dictionary (`mydict`) not found",
    "BAD_TYPE_OF_FIELD",
)


def _case(case_id: str, engine: str, ordered: bool) -> GenerationCase:
    table = ClickHouseTable(
        columns=COLUMNS, engine=engine, order_by='["id"]' if ordered else None
    )
    return GenerationCase(f"engine_{case_id}", "clickhouse", (table.source(),))


def _engine_clause(result) -> str:
    match = re.search(r"ENGINE = ([^\n;]+)", result.steps[0].upgrade)
    return match.group(1).strip() if match else ""


def test_no_engine_produces_a_syntax_error(clickhouse_runner):
    cases = [_case(cid, engine, ordered) for cid, engine, ordered, _ in ENGINES]
    results = clickhouse_runner.run_all(cases, workers=8)
    broken = [
        r for r in results
        if r.verdict() == "server-rejected"
        and not any(marker in r.steps[-1].server_error for marker in ENVIRONMENTAL)
    ]
    assert not broken, (
        "the generated ENGINE clause was malformed, not merely unsatisfiable:\n"
        + "\n".join(f"  {r.case_id}: {_engine_clause(r)}\n      {r.steps[-1].server_error}" for r in broken)
    )


def test_engine_arguments_are_not_dropped(clickhouse_runner):
    expected = {cid: args for cid, _, _, args in ENGINES if args}
    cases = [_case(cid, engine, ordered) for cid, engine, ordered, args in ENGINES if args]
    results = clickhouse_runner.run_all(cases, workers=8)

    lost = []
    for result in results:
        clause = _engine_clause(result)
        key = result.case_id.removeprefix("engine_")
        missing = [arg for arg in expected[key] if arg not in clause]
        if missing:
            lost.append(f"  {key}: {clause!r} lost {missing}")
    assert not lost, (
        "these engine builders accepted parameters and did not render them:\n"
        + "\n".join(lost)
    )


UNORDERED_ENGINES = [(cid, engine) for cid, engine, ordered, _ in ENGINES if not ordered]


def test_order_by_is_not_emitted_for_engines_that_forbid_it(clickhouse_runner):
    """A model that asks for ORDER BY on a Log-family engine must be refused."""
    cases = [
        GenerationCase(
            f"forced_order_{cid}",
            "clickhouse",
            (ClickHouseTable(columns=COLUMNS, engine=engine, order_by='["id"]').source(),),
        )
        for cid, engine in UNORDERED_ENGINES
        if cid in {"memory", "log", "tiny_log", "stripe_log", "null", "set"}
    ]
    results = clickhouse_runner.run_all(cases, workers=6)
    emitted = [r for r in results if "ORDER BY" in r.steps[0].upgrade and r.steps[0].generated]
    assert not emitted, (
        "ORDER BY was emitted for an engine that cannot accept it; dbwarden should "
        "refuse the model instead of letting the server reject the migration:\n"
        + report(emitted)
    )
