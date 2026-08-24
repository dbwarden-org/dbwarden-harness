"""Values that end up inside SQL literals must be escaped, not re-quoted.

Two different rendering bugs live here.

Enum members go through what is evidently Python ``repr()``: a value containing
an apostrophe comes out wrapped in *double* quotes, which ClickHouse does not
accept as a string literal.  Choosing a quote character instead of escaping the
one you have is the classic shape of this bug, and it fails on exactly the
values a real enum is likely to contain.

``SETTINGS`` values are not quoted at all, so anything that is not a bare
identifier or an integer produces a syntax error or a type error.
"""
from __future__ import annotations

import pytest

from tools.case_runner import GenerationCase
from tools.model_source import ClickHouseTable, Column_

pytestmark = pytest.mark.integration

ENUM_VALUES = {
    "apostrophe": """Enum("it's", 'other', name='e_apos')""",
    "double_quote": '''Enum('say "hi"', 'other', name='e_dq')''',
    "both_quotes": '''Enum("""a'b"c""", 'other', name='e_both')''',
    "comma": """Enum('a,b', 'other', name='e_comma')""",
    "empty": """Enum('', 'other', name='e_empty')""",
    "backslash": r"""Enum('a\\b', 'other', name='e_bs')""",
}


@pytest.mark.parametrize("name", sorted(ENUM_VALUES))
def test_enum_members_are_escaped_not_requoted(clickhouse_runner, name):
    table = ClickHouseTable(
        columns=(Column_("id", primary_key=True), Column_("e", ENUM_VALUES[name]))
    )
    result = clickhouse_runner.run(
        GenerationCase(f"enum_{name}", "clickhouse", (table.source(),))
    )
    emitted = next(
        (line.strip() for line in result.steps[0].upgrade.splitlines() if line.strip().startswith("e ")),
        "",
    )
    # Only the *delimiter* matters: a double quote inside a single-quoted
    # literal is fine, a double-quoted literal is not.
    members = emitted.split("(", 1)[-1].rsplit(")", 1)[0]
    delimiters = [part.strip()[:1] for part in _split_members(members) if part.strip()]
    assert set(delimiters) <= {"'"}, (
        "an enum member was wrapped in double quotes instead of having its "
        "apostrophe doubled; ClickHouse string literals are single-quoted:\n"
        f"  {emitted}"
    )
    assert result.verdict() != "server-rejected", (
        f"{emitted}\n  {result.steps[0].server_error}"
    )


def _split_members(members: str) -> list[str]:
    """Split an Enum8(...) argument list on the commas that separate members."""
    parts, depth, current, quote = [], 0, [], None
    for index, character in enumerate(members):
        previous = members[index - 1] if index else ""
        if quote:
            current.append(character)
            if character == quote and previous != "\\":
                quote = None
            continue
        if character in "'\"":
            quote = character
            current.append(character)
        elif character == "(":
            depth += 1
            current.append(character)
        elif character == ")":
            depth -= 1
            current.append(character)
        elif character == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(character)
    parts.append("".join(current))
    return parts


# ``index_granularity`` is numeric and must stay bare; ``storage_policy`` is
# string-typed and must be quoted.  Asserting on the emitted clause rather than
# on the server keeps the test about rendering, not about which storage policies
# happen to exist on the test server.
NUMERIC_SETTING = ("index_granularity", '"4096"', "4096")
STRING_SETTINGS = {
    "plain": '"default"',
    "float_like": '"1.5"',
    "boolean_like": '"true"',
    "empty": '""',
    "with_space": '"a b"',
    "with_apostrophe": "\"it's\"",
}


def _settings_clause(result) -> str:
    return next(
        (line.strip() for line in result.steps[0].upgrade.splitlines() if "SETTINGS" in line),
        "",
    )


def test_numeric_setting_is_emitted_bare(clickhouse_runner):
    """Contrast case: a numeric setting must not acquire quotes."""
    key, declared, expected = NUMERIC_SETTING
    table = ClickHouseTable(settings=f'{{"{key}": {declared}}}')
    result = clickhouse_runner.run(
        GenerationCase("setting_numeric", "clickhouse", (table.source(),))
    )
    assert f"{key}={expected}" in _settings_clause(result).replace(" ", ""), (
        f"expected a bare numeric setting; emitted: {_settings_clause(result)!r}"
    )


@pytest.mark.parametrize("name", sorted(STRING_SETTINGS))
def test_string_setting_values_are_quoted(clickhouse_runner, name):
    table = ClickHouseTable(settings=f'{{"storage_policy": {STRING_SETTINGS[name]}}}')
    result = clickhouse_runner.run(
        GenerationCase(f"setting_{name}", "clickhouse", (table.source(),), apply=False)
    )
    clause = _settings_clause(result)
    value = clause.split("storage_policy", 1)[-1].lstrip(" =").rstrip(";")
    assert value.startswith("'") and value.rstrip().endswith("'"), (
        "a string-typed SETTINGS value was interpolated without quotes, so any "
        "value that is not a bare identifier produces a syntax error:\n"
        f"  {clause}"
    )


def test_comment_newline_does_not_break_the_statement(clickhouse_runner):
    """A newline in a comment must not appear raw inside the migration file."""
    table = ClickHouseTable(comment="line1\nline2")
    result = clickhouse_runner.run(
        GenerationCase("comment_newline", "clickhouse", (table.source(),), apply=False)
    )
    comment_line = next(
        (line for line in result.steps[0].sql.splitlines() if "COMMENT '" in line), ""
    )
    assert comment_line.rstrip().endswith(("'", "';")), (
        "a raw newline was emitted inside a quoted comment, splitting the statement "
        f"across lines in the migration file:\n{result.steps[0].upgrade}"
    )
