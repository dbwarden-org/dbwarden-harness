from __future__ import annotations

import re
from difflib import unified_diff

from sqlglot import ErrorLevel, ParseError, exp, parse
from sqlglot.optimizer.normalize_identifiers import normalize_identifiers

from mcp_server.models import ComparisonResult, ComparisonSummary

DBWARDEN_TABLE_RE = re.compile(r"^(?:_?dbwarden[_-]|dbwarden_)", re.IGNORECASE)


def compare_schemas(dump_a: str, dump_b: str, backend: str = "") -> ComparisonResult:
    norm_a = normalize_schema_dump(dump_a, backend)
    norm_b = normalize_schema_dump(dump_b, backend)
    if norm_a == norm_b:
        return ComparisonResult(identical=True)
    diff = "\n".join(
        unified_diff(
            norm_a.splitlines(),
            norm_b.splitlines(),
            fromfile="track_a/schema_dump.sql",
            tofile="track_b/schema_dump.sql",
            lineterm="",
        )
    )
    actual = _parse_schema(norm_a, backend)
    expected = _parse_schema(norm_b, backend)
    summary = ComparisonSummary(
        missing_tables=sorted(expected.keys() - actual.keys()),
        extra_tables=sorted(actual.keys() - expected.keys()),
    )
    for table in sorted(actual.keys() & expected.keys()):
        for column, expected_type in expected[table].items():
            if column not in actual[table]:
                summary.missing_columns.append({"table": table, "column": column})
            elif actual[table][column] != expected_type:
                summary.type_mismatches.append(
                    {
                        "table": table,
                        "column": column,
                        "expected": expected_type,
                        "actual": actual[table][column],
                    }
                )
    return ComparisonResult(identical=False, diff=diff, summary=summary)


def normalize_schema_dump(dump: str, backend: str = "") -> str:
    """Canonicalize parsed DDL while preserving literals, identifiers and table options.

    Unsupported SQL raises instead of being discarded from the comparison.
    """
    dialect = _dialect(backend)
    statements = []
    for statement in parse(dump, read=dialect, error_level=ErrorLevel.RAISE):
        if statement is None:
            continue
        if isinstance(statement, exp.Command):
            raise ParseError("Unsupported schema statement")
        target = statement.this
        table = target.this if isinstance(target, exp.Schema) else target
        if isinstance(table, exp.Index):
            table = table.args.get("table")
        if isinstance(table, exp.Table) and DBWARDEN_TABLE_RE.match(table.name):
            continue
        for node in statement.walk():
            node.pop_comments()
        if isinstance(statement, exp.Create) and isinstance(target, exp.Schema):
            columns = []
            constraints = []
            for item in target.expressions:
                if not isinstance(item, exp.ColumnDef):
                    constraints.append(item)
                    continue
                if backend == "sqlite" and item.kind.sql(dialect="sqlite").startswith("INTEGER"):
                    spelling = re.match(r"\s*(\w+)", dump[item.this.meta["end"] + 1:])
                    if spelling is None:
                        raise ParseError("Cannot preserve SQLite integer type spelling")
                    item.kind.set("this", exp.DataType.Type.USERDEFINED)
                    item.kind.set("kind", exp.Var(this=spelling.group(1).upper()))
                remaining = []
                for constraint in item.constraints:
                    kind = constraint.kind
                    if (
                        isinstance(kind, exp.PrimaryKeyColumnConstraint)
                        and not any(kind.args.values())
                        and not any(
                            isinstance(c.kind, exp.AutoIncrementColumnConstraint)
                            for c in item.constraints
                        )
                    ):
                        constraints.append(exp.PrimaryKey(expressions=[item.this.copy()]))
                    else:
                        remaining.append(constraint)
                item.set("constraints", remaining)
                columns.append(item)
            target.set(
                "expressions", columns + sorted(constraints, key=lambda c: c.sql(dialect=dialect))
            )
        normalize_identifiers(statement, dialect=dialect)
        statements.append(
            statement.sql(dialect=dialect, identify=True, unsupported_level=ErrorLevel.RAISE)
        )
    return ";\n".join(sorted(statements)) + (";\n" if statements else "")


def _dialect(backend: str) -> str | None:
    return {"postgresql": "postgres", "mariadb": "mysql"}.get(backend, backend) or None


def _parse_schema(dump: str, backend: str) -> dict[str, dict[str, str]]:
    tables = {}
    for statement in parse(dump, read=_dialect(backend)):
        if isinstance(statement, exp.Create) and isinstance(statement.this, exp.Schema):
            tables[statement.this.this.sql()] = {
                column.this.sql(): column.kind.sql()
                for column in statement.this.expressions
                if isinstance(column, exp.ColumnDef)
            }
    return tables
