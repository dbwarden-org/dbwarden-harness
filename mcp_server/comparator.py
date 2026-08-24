from __future__ import annotations

import re
from difflib import unified_diff

from mcp_server.models import ComparisonResult, ComparisonSummary

CREATE_TABLE_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([\"'`]?)(\w+)\1?",
    re.IGNORECASE,
)
CREATE_INDEX_RE = re.compile(
    r"CREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?([\"'`]?)(\w+)\1?",
    re.IGNORECASE,
)
ALTER_TABLE_RE = re.compile(
    r"ALTER\s+TABLE\s+([\"'`]?)(\w+)\1?",
    re.IGNORECASE,
)
COMMENT_RE = re.compile(r"--.*$")
WHITESPACE_RE = re.compile(r"\s+")
DBWARDEN_TABLE_RE = re.compile(r"^(?:_?dbwarden[_-]|dbwarden_)", re.IGNORECASE)


def compare_schemas(
    dump_a: str,
    dump_b: str,
    backend: str = "",
) -> ComparisonResult:
    norm_a = normalize_schema_dump(dump_a, backend=backend)
    norm_b = normalize_schema_dump(dump_b, backend=backend)

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

    schema_a = _parse_schema(norm_a)
    schema_b = _parse_schema(norm_b)
    summary = _summarize_diff(schema_a, schema_b)

    return ComparisonResult(identical=False, diff=diff, summary=summary)


def normalize_schema_dump(dump: str, backend: str = "") -> str:
    """Return a deterministic, comparable representation of a schema dump."""
    # Strip comments and collapse whitespace.
    lines = []
    for raw in dump.splitlines():
        line = COMMENT_RE.sub("", raw)
        line = line.strip()
        if not line:
            continue
        lines.append(line)
    text = " ".join(lines)
    text = WHITESPACE_RE.sub(" ", text)

    # Split into top-level statements heuristically.
    statements = _split_statements(text)

    # Filter out dbwarden bookkeeping tables.
    statements = _filter_dbwarden_statements(statements)

    # Normalize CREATE TABLE constraint placement.
    statements = [_normalize_create_table(stmt) for stmt in statements]

    # Sort by statement kind and object name.
    def sort_key(stmt: str) -> tuple[str, str]:
        stmt_upper = stmt.upper()
        if "CREATE TABLE" in stmt_upper:
            kind = "0_TABLE"
        elif "CREATE INDEX" in stmt_upper:
            kind = "1_INDEX"
        elif "ALTER TABLE" in stmt_upper:
            kind = "2_ALTER"
        else:
            kind = "3_OTHER"
        name = _extract_object_name(stmt) or ""
        return (kind, name.lower())

    statements.sort(key=sort_key)
    return "\n".join(_normalize_statement(stmt) for stmt in statements) + "\n"


def _filter_dbwarden_statements(statements: list[str]) -> list[str]:
    filtered: list[str] = []
    for stmt in statements:
        name = _extract_object_name(stmt)
        if name and DBWARDEN_TABLE_RE.match(name):
            continue
        filtered.append(stmt)
    return filtered


def _normalize_create_table(statement: str) -> str:
    """Move inline PRIMARY KEY and UNIQUE constraints to canonical separate form."""
    match = CREATE_TABLE_RE.search(statement)
    if not match:
        return statement

    table = match.group(2)
    start = statement.find("(")
    if start == -1:
        return statement

    depth = 0
    end = -1
    for i, ch in enumerate(statement[start:], start=start):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end == -1:
        return statement

    body = statement[start + 1 : end]
    columns: list[str] = []
    primary_keys: list[str] = []
    unique_sets: list[list[str]] = []

    for raw_item in _split_columns(body):
        item = raw_item.strip()
        if not item:
            continue

        # Preserve already-separated table-level constraints.
        if re.match(r"^(PRIMARY\s+KEY|UNIQUE|FOREIGN\s+KEY|CHECK|CONSTRAINT)\b", item, re.IGNORECASE):
            columns.append(item)
            continue

        # Extract inline PRIMARY KEY.
        pk_match = re.search(r"\bPRIMARY\s+KEY\b", item, re.IGNORECASE)
        if pk_match:
            col_name = item.split(None, 1)[0]
            primary_keys.append(col_name)
            item = re.sub(r"\s*\bPRIMARY\s+KEY\b", "", item, flags=re.IGNORECASE).strip()

        # Extract inline UNIQUE.
        unique_match = re.search(r"\bUNIQUE\b", item, re.IGNORECASE)
        if unique_match:
            col_name = item.split(None, 1)[0]
            unique_sets.append([col_name])
            item = re.sub(r"\s*\bUNIQUE\b", "", item, flags=re.IGNORECASE).strip()

        if item:
            columns.append(item)

    parts = [f"CREATE TABLE {table} ("]
    parts.append(", ".join(columns))
    if primary_keys:
        parts.append(f", PRIMARY KEY ({', '.join(primary_keys)})")
    for unique_cols in unique_sets:
        parts.append(f", UNIQUE ({', '.join(unique_cols)})")
    parts.append(")")
    return "".join(parts)


def _split_columns(body: str) -> list[str]:
    """Split a CREATE TABLE body on top-level commas."""
    items: list[str] = []
    current: list[str] = []
    depth = 0
    for token in re.split(r"(\(|\)|,)", body):
        if token == "(":
            depth += 1
        elif token == ")":
            depth -= 1
        elif token == "," and depth == 0:
            if current:
                items.append("".join(current))
                current = []
            continue
        current.append(token)
    if current:
        items.append("".join(current))
    return [item.strip() for item in items if item.strip()]


def _split_statements(text: str) -> list[str]:
    statements: list[str] = []
    current = []
    depth = 0
    for token in re.split(r"(\(|\)|;)", text):
        if token == "(":
            depth += 1
        elif token == ")":
            depth -= 1
        elif token == ";" and depth == 0:
            if current:
                statements.append("".join(current).strip())
                current = []
            continue
        current.append(token)
    if current:
        statements.append("".join(current).strip())
    return [s for s in statements if s]


def _extract_object_name(statement: str) -> str | None:
    for pattern in (CREATE_TABLE_RE, CREATE_INDEX_RE, ALTER_TABLE_RE):
        match = pattern.search(statement)
        if match:
            return match.group(2)
    return None


def _normalize_statement(statement: str) -> str:
    # Normalize identifier quoting: prefer unquoted lowercase identifiers.
    statement = re.sub(r"[`\"]([a-zA-Z_][a-zA-Z0-9_]*)[`\"]", lambda m: m.group(1).lower(), statement)
    statement = WHITESPACE_RE.sub(" ", statement).strip()
    return statement


def _parse_schema(norm: str) -> dict[str, dict[str, str]]:
    """Return {table: {column: type_signature}} extracted from normalized CREATE TABLE statements."""
    schema: dict[str, dict[str, str]] = {}
    for statement in norm.splitlines():
        match = CREATE_TABLE_RE.search(statement)
        if not match:
            continue
        table = match.group(2).lower()
        start = statement.find("(")
        if start == -1:
            continue
        depth = 0
        end = -1
        for i, ch in enumerate(statement[start:], start=start):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end == -1:
            continue
        columns: dict[str, str] = {}
        for col_line in _split_columns(statement[start + 1 : end]):
            parts = col_line.split(None, 2)
            if len(parts) < 2:
                continue
            col_name = re.sub(r"[`\"']", "", parts[0]).lower()
            col_type = parts[1].lower()
            columns[col_name] = col_type
        schema[table] = columns
    return schema


def _summarize_diff(
    schema_a: dict[str, dict[str, str]],
    schema_b: dict[str, dict[str, str]],
) -> ComparisonSummary:
    summary = ComparisonSummary()

    a_tables = set(schema_a)
    b_tables = set(schema_b)

    summary.missing_tables = sorted(a_tables - b_tables)
    summary.extra_tables = sorted(b_tables - a_tables)

    for table in sorted(a_tables & b_tables):
        a_cols = schema_a[table]
        b_cols = schema_b[table]
        for col in sorted(a_cols):
            if col not in b_cols:
                summary.missing_columns.append({"table": table, "column": col})
            elif a_cols[col] != b_cols[col]:
                summary.type_mismatches.append(
                    {
                        "table": table,
                        "column": col,
                        "expected": b_cols[col],
                        "actual": a_cols[col],
                    }
                )

    return summary
