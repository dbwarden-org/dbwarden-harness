"""One property changed per case: does dbwarden generate a migration for it?

Each case declares a ClickHouse table, migrates it, then changes exactly one
property and runs ``make-migrations`` again.  Both revisions declare the same
columns, so nothing is confounded by an incidental column add or drop — a
mistake that is easy to make by hand and that silently turns a "property change"
case into an "add column" case.

The contract asserted here is the one the documentation states: a supported
change produces a migration, and an unsupported change produces an error.
Producing *neither* — exit 0, no file, "all models already covered" — leaves the
database permanently out of sync with the model with nothing to alert the user,
and is the failure this suite exists to catch.
"""
from __future__ import annotations

import pytest

from tools.case_runner import GenerationCase, report
from tools.model_source import ClickHouseTable, Column_

pytestmark = pytest.mark.integration

BASE = ClickHouseTable(
    columns=(Column_("id", primary_key=True), Column_("a")),
)
WITH_TS = BASE.with_(
    columns=(Column_("id", primary_key=True), Column_("a"), Column_("ts", "DateTime"))
)
STRING_COL = BASE.with_(columns=(Column_("id", primary_key=True), Column_("a", "String")))


def _meta(table: ClickHouseTable, spec: str) -> ClickHouseTable:
    return table.with_(column_meta={"a": spec})


# (case_id, before, after, documented_as)
#   "allowed"     - docs/databases/clickhouse/declaring-tables.md says this change is supported
#   "forbidden"   - docs say it is never allowed; dbwarden must refuse, not ignore
#   "expected"    - not documented either way, but a schema tool must not lose it
CHANGES: list[tuple[str, ClickHouseTable, ClickHouseTable, str]] = [
    ("codec_change", _meta(BASE, 'codec="ZSTD(1)"'), _meta(BASE, 'codec="ZSTD(9)"'), "expected"),
    ("codec_remove", _meta(BASE, 'codec="ZSTD(1)"'), BASE, "expected"),
    ("codec_add", BASE, _meta(BASE, 'codec="ZSTD(1)"'), "expected"),
    ("default_change", _meta(BASE, 'default_expression="1"'), _meta(BASE, 'default_expression="2"'), "expected"),
    ("default_remove", _meta(BASE, 'default_expression="1"'), BASE, "expected"),
    ("materialized_change", _meta(BASE, 'materialized="id*2"'), _meta(BASE, 'materialized="id*3"'), "expected"),
    ("alias_change", _meta(BASE, 'alias="id+1"'), _meta(BASE, 'alias="id+2"'), "expected"),
    ("nullable_on", BASE, _meta(BASE, "nullable=True"), "expected"),
    ("nullable_off", _meta(BASE, "nullable=True"), BASE, "expected"),
    ("lowcardinality_on", STRING_COL, _meta(STRING_COL, "low_cardinality=True"), "expected"),
    ("lowcardinality_off", _meta(STRING_COL, "low_cardinality=True"), STRING_COL, "expected"),
    ("type_override_change", _meta(BASE, 'type="Int64"'), _meta(BASE, 'type="Int128"'), "expected"),
    ("column_ttl_change",
     _meta(WITH_TS, 'ttl="ts + toIntervalDay(1)"'),
     _meta(WITH_TS, 'ttl="ts + toIntervalDay(9)"'), "expected"),
    ("column_comment_change", BASE.with_(column_comments={"a": "x"}), BASE.with_(column_comments={"a": "y"}), "expected"),
    ("table_comment_change", BASE.with_(comment="x"), BASE.with_(comment="y"), "expected"),
    ("table_comment_remove", BASE.with_(comment="x"), BASE, "expected"),
    ("table_comment_add", BASE, BASE.with_(comment="new"), "expected"),
    ("settings_add", BASE, BASE.with_(settings='{"index_granularity":"4096"}'), "allowed"),
    ("settings_change",
     BASE.with_(settings='{"index_granularity":"4096"}'),
     BASE.with_(settings='{"index_granularity":"8192"}'), "allowed"),
    ("settings_remove", BASE.with_(settings='{"index_granularity":"4096"}'), BASE, "allowed"),
    ("ttl_add", WITH_TS, WITH_TS.with_(ttl='["ts + toIntervalDay(1)"]'), "allowed"),
    ("ttl_change",
     WITH_TS.with_(ttl='["ts + toIntervalDay(1)"]'),
     WITH_TS.with_(ttl='["ts + toIntervalDay(9)"]'), "allowed"),
    ("partition_add", WITH_TS, WITH_TS.with_(partition_by='"toYYYYMM(ts)"'), "forbidden"),
    ("sample_add", BASE, BASE.with_(sample_by='"id"'), "forbidden"),
    ("order_by_extend", BASE, BASE.with_(order_by='["id","a"]'), "allowed"),
    ("primary_key_add", BASE, BASE.with_(primary_key='["id"]'), "expected"),
    ("index_add", BASE, BASE.with_(indexes='[skip_index("ix",["a"],"minmax")]'), "allowed"),
    ("index_granularity",
     BASE.with_(indexes='[skip_index("ix",["a"],"minmax",granularity=1)]'),
     BASE.with_(indexes='[skip_index("ix",["a"],"minmax",granularity=8)]'), "allowed"),
    ("index_type",
     BASE.with_(indexes='[skip_index("ix",["a"],"minmax")]'),
     BASE.with_(indexes='[skip_index("ix",["a"],"set(100)")]'), "allowed"),
    ("index_rename",
     BASE.with_(indexes='[skip_index("ix1",["a"],"minmax")]'),
     BASE.with_(indexes='[skip_index("ix2",["a"],"minmax")]'), "allowed"),
    ("index_remove", BASE.with_(indexes='[skip_index("ix",["a"],"minmax")]'), BASE, "allowed"),
    ("projection_add", BASE, BASE.with_(projections='[projection("p","SELECT a, count() GROUP BY a")]'), "allowed"),
    ("projection_query",
     BASE.with_(projections='[projection("p","SELECT a, count() GROUP BY a")]'),
     BASE.with_(projections='[projection("p","SELECT a, sum(a) GROUP BY a")]'), "allowed"),
    ("projection_rename",
     BASE.with_(projections='[projection("p1","SELECT a ORDER BY a")]'),
     BASE.with_(projections='[projection("p2","SELECT a ORDER BY a")]'), "allowed"),
    ("projection_remove", BASE.with_(projections='[projection("p","SELECT a ORDER BY a")]'), BASE, "allowed"),
    ("type_widen_string", STRING_COL, BASE.with_(columns=(Column_("id", primary_key=True), Column_("a", "Text"))), "expected"),
    ("type_int_to_float", BASE, BASE.with_(columns=(Column_("id", primary_key=True), Column_("a", "Float"))), "expected"),
    ("type_int_to_bigint", BASE, BASE.with_(columns=(Column_("id", primary_key=True), Column_("a", "BigInteger"))), "expected"),
    ("type_int_to_string", BASE, STRING_COL, "expected"),
    ("column_reorder",
     BASE.with_(columns=(Column_("id", primary_key=True), Column_("a"), Column_("b"))),
     BASE.with_(columns=(Column_("id", primary_key=True), Column_("b"), Column_("a")))),
]


def _cases() -> list[GenerationCase]:
    cases = []
    for entry in CHANGES:
        case_id, before, after = entry[0], entry[1], entry[2]
        cases.append(
            GenerationCase(
                case_id=case_id,
                backend="clickhouse",
                revisions=(before.source(), after.source()),
                capture_schema=True,
            )
        )
    return cases


def test_every_property_change_is_represented(clickhouse_runner):
    """A changed property must produce a migration or an explicit refusal."""
    results = clickhouse_runner.run_all(_cases(), workers=8)

    setup_failures = [r for r in results if not r.steps or not r.steps[0].generated]
    assert not setup_failures, (
        "these cases never established a baseline, so the change under test was "
        f"not actually exercised:\n{report(setup_failures)}"
    )

    ignored = [r for r in results if r.steps[-1].verdict() == "no-migration"]
    assert not ignored, (
        f"{len(ignored)} of {len(results)} property changes produced no migration "
        "and no error - the database is left out of sync with the model with no "
        f"signal to the user:\n{report(ignored)}"
    )


def test_documented_forbidden_changes_are_refused(clickhouse_runner):
    """Changes the docs call impossible must fail loudly, not pass silently."""
    forbidden = [entry for entry in CHANGES if len(entry) > 3 and entry[3] == "forbidden"]
    cases = [
        GenerationCase(
            case_id=entry[0],
            backend="clickhouse",
            revisions=(entry[1].source(), entry[2].source()),
        )
        for entry in forbidden
    ]
    results = clickhouse_runner.run_all(cases, workers=4)
    passed_silently = [r for r in results if r.steps[-1].verdict() == "no-migration"]
    assert not passed_silently, (
        "docs/databases/clickhouse/declaring-tables.md documents these as never "
        "allowed; dbwarden accepted the model and generated nothing:\n"
        f"{report(passed_silently)}"
    )
