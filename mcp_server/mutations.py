from __future__ import annotations

import re
from typing import Any


class MutationError(ValueError):
    """Raised when a mutation cannot be applied to the model source."""


# Regex matching a column declaration line inside a SQLAlchemy class body.
COLUMN_LINE_RE = re.compile(
    r"^(?P<indent>\s+)(?P<name>\w+):\s*Mapped\[.*?\]\s*=\s*mapped_column\((?P<args>.*?)\)\s*$",
    re.MULTILINE,
)


def apply_mutation(source: str, mutation: dict[str, Any]) -> str:
    """Best-effort source transformation for a single model mutation.

    The harness does not require this function to be perfect; callers may also
    use ``write_model_file`` to supply an arbitrary model source.
    """
    mutation_type = mutation.get("type")
    handlers = {
        "add_column": _add_column,
        "change_type": _change_type,
        "add_index": _add_index,
        "drop_column": _drop_column,
        "set_not_null": _set_not_null,
        "drop_not_null": _drop_not_null,
        "set_default": _set_default,
        "drop_default": _drop_default,
    }
    handler = handlers.get(mutation_type)
    if handler is None:
        raise MutationError(f"Unsupported mutation type: {mutation_type}")
    return handler(source, mutation)


def _find_class_for_table(source: str, table: str) -> tuple[int, int, str]:
    """Return (start, end, indent) for the class body of ``table``."""
    class_re = re.compile(rf"^class\s+\w+\(.*\):\s*$\s+__tablename__\s*=\s*['\"]{re.escape(table)}['\"]", re.MULTILINE)
    match = class_re.search(source)
    if not match:
        raise MutationError(f"Table {table!r} not found in model source")
    body_start = match.end()

    # Find the next top-level class or end of file.
    next_class = re.compile(r"^class\s+\w+\(.*\):\s*$", re.MULTILINE).search(source, body_start)
    body_end = next_class.start() if next_class else len(source)

    # Determine indentation of first body line.
    body = source[body_start:body_end]
    indent_match = re.search(r"^(\s+)\S", body, re.MULTILINE)
    indent = indent_match.group(1) if indent_match else "    "
    return body_start, body_end, indent


def _add_column(source: str, mutation: dict[str, Any]) -> str:
    table = mutation["table"]
    column = mutation["column"]
    column_type = mutation["column_type"]
    nullable = mutation.get("nullable", True)
    default = mutation.get("default")

    _body_start, body_end, indent = _find_class_for_table(source, table)
    args = f"{column_type}, nullable={nullable}"
    if default is not None:
        args += f", default={default!r}"
    new_line = f"{indent}{column}: Mapped[{column_type}] = mapped_column({args})\n"

    return source[:body_end] + new_line + source[body_end:]


def _change_type(source: str, mutation: dict[str, Any]) -> str:
    table = mutation["table"]
    column = mutation["column"]
    new_type = mutation["new_type"]

    body_start, body_end, _ = _find_class_for_table(source, table)
    body = source[body_start:body_end]
    pattern = re.compile(
        rf"^(?P<indent>\s+)(?P<name>{re.escape(column)}):\s*Mapped\[[^\]]+\]\s*=\s*mapped_column\((?P<args>.*?)\)\s*$",
        re.MULTILINE,
    )

    def replacer(match: re.Match[str]) -> str:
        args = match.group("args")
        rest = re.sub(r"^[^,]+", "", args).lstrip(", ")
        new_line = f"{match.group('indent')}{column}: Mapped[{new_type}] = mapped_column({new_type}"
        if rest:
            new_line += f", {rest}"
        new_line += ")"
        return new_line

    new_body, count = pattern.subn(replacer, body)
    if count == 0:
        raise MutationError(f"Could not change type of column {column!r} in table {table!r}")
    return source[:body_start] + new_body + source[body_end:]


def _add_index(source: str, mutation: dict[str, Any]) -> str:
    table = mutation["table"]
    columns = mutation["columns"]
    unique = mutation.get("unique", False)

    body_start, body_end, _indent = _find_class_for_table(source, table)
    body = source[body_start:body_end]

    # First try to add index=True to the first listed column.
    for column in columns:
        col_re = re.compile(
            rf"(?P<line>\s+{re.escape(column)}:\s*Mapped\[.*?\]\s*=\s*mapped_column\()(?P<args>.*?)(?P<close>\)\s*$)",
            re.MULTILINE,
        )
        if "index=True" not in body:
            new_body, count = col_re.subn(
                lambda m: f"{m.group('line')}{m.group('args')}, index=True{m.group('close')}",
                body,
                count=1,
            )
            if count:
                return source[:body_start] + new_body + source[body_end:]

    # Otherwise append a Meta index spec if one exists.
    meta_re = re.compile(r"(?P<indent>\s+)class\s+Meta\(TableMeta\):", re.MULTILINE)
    if meta_re.search(body):
        index_entry = f"{columns!r}"
        # Insert into an existing indexes list or add one.
        indexes_re = re.compile(r"(?P<prefix>indexes:\s*ClassVar\s*=\s*\[)(?P<items>.*?)(?P<suffix>\])", re.DOTALL)
        new_body, count = indexes_re.subn(
            lambda m: f"{m.group('prefix')}{m.group('items')}{', ' if m.group('items').strip() else ''}IndexSpec(name='ix_{table}_{'_'.join(columns)}', columns={index_entry}, unique={unique}){m.group('suffix')}",
            body,
        )
        if count:
            return source[:body_start] + new_body + source[body_end:]

    raise MutationError(f"Could not add index to table {table!r}")


def _drop_column(source: str, mutation: dict[str, Any]) -> str:
    table = mutation["table"]
    column = mutation["column"]
    body_start, body_end, _ = _find_class_for_table(source, table)
    body = source[body_start:body_end]
    lines = body.splitlines(keepends=True)
    filtered = [
        line
        for line in lines
        if not re.match(rf"\s+{re.escape(column)}:\s*Mapped", line)
    ]
    if len(filtered) == len(lines):
        raise MutationError(f"Column {column!r} not found in table {table!r}")
    return source[:body_start] + "".join(filtered) + source[body_end:]


def _set_not_null(source: str, mutation: dict[str, Any]) -> str:
    return _toggle_nullable(source, mutation, nullable=False)


def _drop_not_null(source: str, mutation: dict[str, Any]) -> str:
    return _toggle_nullable(source, mutation, nullable=True)


def _toggle_nullable(source: str, mutation: dict[str, Any], nullable: bool) -> str:
    table = mutation["table"]
    column = mutation["column"]
    body_start, body_end, _ = _find_class_for_table(source, table)
    body = source[body_start:body_end]

    col_re = re.compile(
        rf"(?P<prefix>\s+{re.escape(column)}:\s*Mapped\[.*?\]\s*=\s*mapped_column\()(?P<args>.*?)(?P<suffix>\)\s*$)",
        re.MULTILINE,
    )

    def replacer(match: re.Match[str]) -> str:
        args = match.group("args")
        args = re.sub(r",?\s*nullable\s*=\s*(True|False)", "", args)
        args += f", nullable={nullable}"
        return f"{match.group('prefix')}{args}{match.group('suffix')}"

    new_body, count = col_re.subn(replacer, body)
    if count == 0:
        raise MutationError(f"Column {column!r} not found in table {table!r}")
    return source[:body_start] + new_body + source[body_end:]


def _set_default(source: str, mutation: dict[str, Any]) -> str:
    table = mutation["table"]
    column = mutation["column"]
    default = mutation["default"]
    body_start, body_end, _ = _find_class_for_table(source, table)
    body = source[body_start:body_end]

    col_re = re.compile(
        rf"(?P<prefix>\s+{re.escape(column)}:\s*Mapped\[.*?\]\s*=\s*mapped_column\()(?P<args>.*?)(?P<suffix>\)\s*$)",
        re.MULTILINE,
    )

    def replacer(match: re.Match[str]) -> str:
        args = re.sub(r",?\s*default\s*=\s*[^,)]+", "", match.group("args"))
        args += f", default={default!r}"
        return f"{match.group('prefix')}{args}{match.group('suffix')}"

    new_body, count = col_re.subn(replacer, body)
    if count == 0:
        raise MutationError(f"Column {column!r} not found in table {table!r}")
    return source[:body_start] + new_body + source[body_end:]


def _drop_default(source: str, mutation: dict[str, Any]) -> str:
    table = mutation["table"]
    column = mutation["column"]
    body_start, body_end, _ = _find_class_for_table(source, table)
    body = source[body_start:body_end]

    col_re = re.compile(
        rf"(?P<prefix>\s+{re.escape(column)}:\s*Mapped\[.*?\]\s*=\s*mapped_column\()(?P<args>.*?)(?P<suffix>\)\s*$)",
        re.MULTILINE,
    )

    def replacer(match: re.Match[str]) -> str:
        args = re.sub(r",?\s*default\s*=\s*[^,)]+", "", match.group("args"))
        return f"{match.group('prefix')}{args}{match.group('suffix')}"

    new_body, count = col_re.subn(replacer, body)
    if count == 0:
        raise MutationError(f"Column {column!r} not found in table {table!r}")
    return source[:body_start] + new_body + source[body_end:]
