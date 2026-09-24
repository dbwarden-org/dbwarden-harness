"""Every SQLAlchemy type must map to a ClickHouse type, or be refused.

The mapper has no fallback: a type it does not recognise is rendered into the
DDL by name.  Some of those names are ClickHouse aliases that silently mean
something else (``SET`` becomes ``UInt64``), and some are rejected outright
(``JSONB``).  Both outcomes are worse than a clear "this type has no ClickHouse
equivalent", which is what a cross-backend tool owes its users.

The matrix asserts three things: the generated DDL is accepted by a real server,
the emitted type is not simply the SQLAlchemy spelling echoed back, and the
declared width/precision is not silently dropped.
"""
from __future__ import annotations

import re

import pytest

from tools.case_runner import GenerationCase, report
from tools.model_source import clickhouse_single_column

pytestmark = pytest.mark.integration

# Types every backend-agnostic model is likely to contain.
PORTABLE_TYPES = [
    "SmallInteger", "Integer", "BigInteger", "Float", "Float(24)", "REAL",
    "Numeric", "Numeric(9,2)", "Numeric(38,10)",
    "String", "String(50)", "Text", "Unicode(30)", "UnicodeText",
    "CHAR(8)", "VARCHAR(64)", "CLOB",
    "Boolean", "LargeBinary", "LargeBinary(16)", "BLOB",
    "Date", "DateTime", "DateTime(timezone=True)", "TIMESTAMP", "Time", "Interval",
    "JSON", "Uuid", "ARRAY(Integer)", "PickleType",
]

# Types spelled with a dialect prefix; a portable tool should still map them.
DIALECT_TYPES = [
    "pgd.JSONB", "pgd.INET", "pgd.UUID",
    "myd.TINYINT", "myd.MEDIUMINT", "myd.YEAR", 'myd.SET("a","b")', "myd.BIT(8)",
]

DIALECT_PREAMBLE = "from sqlalchemy.dialects import postgresql as pgd, mysql as myd\n"


def _case(column_type: str, preamble: str = "") -> GenerationCase:
    source = clickhouse_single_column(column_type)
    if preamble:
        source = source.replace("Base = declarative_base()", preamble + "Base = declarative_base()")
    return GenerationCase(
        case_id=f"type_{re.sub(r'[^A-Za-z0-9]+', '_', column_type)}",
        backend="clickhouse",
        revisions=(source,),
        capture_schema=True,
    )


def _emitted_type(result) -> str:
    match = re.search(r"^\s+c (.+?),?$", result.steps[0].upgrade, re.MULTILINE)
    return match.group(1).strip() if match else ""


def test_portable_types_are_accepted_by_the_server(clickhouse_runner):
    results = clickhouse_runner.run_all([_case(t) for t in PORTABLE_TYPES], workers=8)
    rejected = [r for r in results if r.verdict() == "server-rejected"]
    assert not rejected, "generated DDL was rejected by ClickHouse:\n" + report(rejected)


def test_dialect_types_are_mapped_or_refused(clickhouse_runner):
    results = clickhouse_runner.run_all(
        [_case(t, DIALECT_PREAMBLE) for t in DIALECT_TYPES], workers=8
    )
    rejected = [r for r in results if r.verdict() == "server-rejected"]
    assert not rejected, (
        "a dialect-specific type was echoed into ClickHouse DDL by name and the "
        "server rejected it; dbwarden should map it or refuse the model:\n"
        + report(rejected)
    )


def test_no_type_is_echoed_back_as_its_sqlalchemy_spelling(clickhouse_runner):
    """A ClickHouse type name must not be a SQLAlchemy/other-dialect name."""
    cases = [_case(t) for t in PORTABLE_TYPES] + [
        _case(t, DIALECT_PREAMBLE) for t in DIALECT_TYPES
    ]
    results = clickhouse_runner.run_all(cases, workers=8)

    # ClickHouse type names are CamelCase (Int32, LowCardinality, DateTime64);
    # SQL/dialect spellings that leak through are SHOUTING or unknown families.
    leaked = []
    for result in results:
        emitted = _emitted_type(result)
        head = emitted.split("(")[0].strip()
        if head and head.isupper() and head not in {"JSON"}:
            leaked.append(f"  {result.case_id}: emitted {emitted!r}")
    assert not leaked, (
        "these columns were rendered with a non-ClickHouse type name, which means "
        "the mapper fell through rather than mapping:\n" + "\n".join(leaked)
    )


WIDTH_SENSITIVE = {
    "CHAR(8)": "8",
    "String(50)": "50",
    "LargeBinary(16)": "16",
    "Numeric(9,2)": "9",
}


@pytest.mark.parametrize("column_type,width", sorted(WIDTH_SENSITIVE.items()))
def test_declared_width_is_not_silently_dropped(clickhouse_runner, column_type, width):
    result = clickhouse_runner.run(_case(column_type))
    emitted = _emitted_type(result)
    assert width in emitted, (
        f"{column_type} lost its declared width: emitted {emitted!r}. ClickHouse has "
        "FixedString(N) and Decimal(P,S) for exactly this."
    )
