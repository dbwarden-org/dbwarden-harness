"""Model-supplied text must never be able to close a DDL statement.

dbwarden already escapes the two things that look like escaping problems --
identifiers are backquote-doubled and comments are apostrophe-doubled -- so a
spot check of either one passes.  The channels that matter are the ones that
carry *expressions*: engine arguments, ORDER BY / PARTITION BY / SAMPLE BY / TTL,
settings values, index and projection names and bodies, column defaults, codecs
and raw type overrides.  Those are concatenated verbatim.

Each case plants the same payload and asserts that it does not survive into the
generated migration as executable SQL.  A payload that reaches the file is a
finding whether or not the server happens to reject it: the migration file is
committed to a repository and applied later, by a different person.
"""
from __future__ import annotations

import pytest

from tools.case_runner import GenerationCase
from tools.model_source import ClickHouseTable, Column_

pytestmark = pytest.mark.integration

PAYLOAD = "; DROP TABLE t; --"
BASE = ClickHouseTable(columns=(Column_("id", primary_key=True), Column_("s", "String")))

CHANNELS: dict[str, ClickHouseTable] = {
    "order_by": BASE.with_(order_by=f'["id) {PAYLOAD}"]'),
    "partition_by": BASE.with_(partition_by=f'"1{PAYLOAD}"'),
    "sample_by": BASE.with_(sample_by=f'"id) {PAYLOAD}"'),
    "ttl": BASE.with_(ttl=f'["now(){PAYLOAD}"]'),
    "settings_value": BASE.with_(settings=f'{{"index_granularity":"1{PAYLOAD}"}}'),
    "primary_key": BASE.with_(primary_key=f'["id) {PAYLOAD}"]'),
    "index_name": BASE.with_(
        indexes=f'[skip_index("ix (s) TYPE minmax GRANULARITY 1{PAYLOAD}",["s"],"minmax")]'
    ),
    "projection_body": BASE.with_(
        projections=f'[projection("p","SELECT s) {PAYLOAD}")]'
    ),
    "default_expression": BASE.with_(column_meta={"s": f'default_expression="1{PAYLOAD}"'}),
    "codec": BASE.with_(column_meta={"s": f'codec="ZSTD(3)) {PAYLOAD}"'}),
    "type_override": BASE.with_(column_meta={"s": f'type="String) {PAYLOAD}"'}),
}


def test_no_channel_admits_a_statement_terminator(clickhouse_runner):
    cases = [
        GenerationCase(f"inject_{name}", "clickhouse", (table.source(),), apply=False)
        for name, table in CHANNELS.items()
    ]
    results = clickhouse_runner.run_all(cases, workers=6)

    leaked = []
    for result in results:
        if not result.steps or not result.steps[0].sql:
            continue
        sql = result.steps[0].sql
        if "DROP TABLE t;" in sql or "DROP TABLE t --" in sql:
            leaked.append(result)

    assert not leaked, (
        f"{len(leaked)} of {len(CHANNELS)} channels interpolated a statement "
        "terminator straight into the migration file:\n"
        + "\n".join(f"  {r.case_id}: {_offending_line(r)}" for r in leaked)
    )


def _offending_line(result) -> str:
    for line in result.steps[0].sql.splitlines():
        if "DROP TABLE t" in line:
            return line.strip()[:140]
    return result.steps[0].upgrade[:140]


def test_identifier_and_comment_escaping_still_holds(clickhouse_runner):
    """Contrast case: the channels that *are* escaped must stay escaped."""
    quoted = ClickHouseTable(
        columns=(Column_("id", primary_key=True), Column_("x", "Integer")),
        comment="it's a table",
    )
    source = quoted.source().replace(
        '    x = Column(Integer)', "    x = Column('has`tick', Integer)"
    )
    result = clickhouse_runner.run(
        GenerationCase("escaping_holds", "clickhouse", (source,), apply=False)
    )
    sql = result.steps[0].sql
    assert "``" in sql, f"backquote in an identifier was not doubled:\n{sql}"
    assert "it''s" in sql, f"apostrophe in a comment was not doubled:\n{sql}"
