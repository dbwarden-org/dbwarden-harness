"""A migration's rollback must invert that migration, not a different one.

The interesting case is a *chain*: several migrations against the same table.
A single migration that adds three columns inverts correctly, so a suite that
only ever writes one migration per table cannot see the defect.  These tests
build chains, then actually run ``dbwarden rollback`` and read the live schema
back, because a rollback that reports success while dropping the wrong object is
worse than one that fails.
"""
from __future__ import annotations

import re

import pytest

from tools.case_runner import GenerationCase
from tools.model_source import ClickHouseTable, Column_

pytestmark = pytest.mark.integration

ID = Column_("id", primary_key=True)


def _chain(*column_sets: tuple[Column_, ...]) -> tuple[str, ...]:
    return tuple(ClickHouseTable(columns=columns).source() for columns in column_sets)


CHAIN = _chain(
    (ID, Column_("a")),
    (ID, Column_("a"), Column_("b")),
    (ID, Column_("a"), Column_("b"), Column_("c", "Float")),
    (ID, Column_("a"), Column_("b"), Column_("c", "Float"), Column_("d", "String")),
)


def _live_columns(schema: str) -> tuple[str, ...]:
    return tuple(re.findall(r"`(\w+)`\s", schema))


def test_each_migration_rolls_back_the_column_it_added(clickhouse_runner):
    """The Nth migration's rollback must name the Nth migration's column."""
    result = clickhouse_runner.run(
        GenerationCase("chain_rollback_text", "clickhouse", CHAIN, capture_schema=True)
    )
    mismatches = []
    for step in result.steps[1:]:
        added = re.search(r"ADD COLUMN (\w+)", step.upgrade)
        dropped = re.search(r"DROP COLUMN (\w+)", step.rollback)
        if added and dropped and added.group(1) != dropped.group(1):
            mismatches.append(
                f"migration {step.index}: upgrade adds {added.group(1)!r} "
                f"but rollback drops {dropped.group(1)!r}"
            )
    assert not mismatches, "rollback targets the wrong column:\n" + "\n".join(mismatches)


def test_rollback_restores_the_previous_schema(clickhouse_runner):
    """Executed rollback must remove exactly the last migration's column."""
    result = clickhouse_runner.run(
        GenerationCase(
            "chain_rollback_applied", "clickhouse", CHAIN, rollback=1, capture_schema=True
        )
    )
    assert result.rollback_returncode == 0, result.rollback_output[-2000:]
    remaining = _live_columns(result.schema_after_rollback)
    assert "d" not in remaining, (
        "rollback of the migration that added 'd' left 'd' in place; live columns: "
        f"{remaining}"
    )
    assert "b" in remaining, (
        "rollback of the migration that added 'd' destroyed unrelated column 'b'; "
        f"live columns: {remaining}"
    )


def test_multi_step_rollback_unwinds_the_whole_chain(clickhouse_runner):
    """``rollback --count N`` must unwind N migrations, not fail partway."""
    result = clickhouse_runner.run(
        GenerationCase(
            "chain_rollback_three", "clickhouse", CHAIN, rollback=3, capture_schema=True
        )
    )
    assert result.rollback_returncode == 0, (
        "rollback --count 3 failed partway, leaving the schema and the migration "
        f"history disagreeing:\n{result.rollback_output[-2000:]}"
    )
    remaining = _live_columns(result.schema_after_rollback)
    assert set(remaining) == {"id", "a"}, (
        f"expected the chain to unwind back to (id, a); live columns: {remaining}"
    )


def test_online_and_offline_generation_agree_on_rollback(clickhouse_runner):
    """The same chain must invert identically whichever diff source is used."""
    online = clickhouse_runner.run(
        GenerationCase("invert_online", "clickhouse", CHAIN[:3])
    )
    offline = clickhouse_runner.run(
        GenerationCase(
            "invert_offline", "clickhouse", CHAIN[:3],
            flags=((), ("--offline",), ("--offline",)),
        )
    )
    online_rollbacks = [step.rollback for step in online.steps[1:]]
    offline_rollbacks = [step.rollback for step in offline.steps[1:]]
    assert online_rollbacks == offline_rollbacks, (
        "make-migrations and make-migrations --offline produced different rollback "
        "SQL for identical model revisions, so whether a project's rollbacks are "
        "correct depends on which flag the team happens to use.\n"
        f"online:  {online_rollbacks}\noffline: {offline_rollbacks}"
    )


def test_single_migration_with_several_columns_inverts_in_reverse_order(clickhouse_runner):
    """Contrast case: intra-migration inversion is expected to be correct."""
    result = clickhouse_runner.run(
        GenerationCase(
            "multi_add_single_migration",
            "clickhouse",
            _chain((ID, Column_("a")), (ID, Column_("a"), Column_("b"), Column_("c", "Float"))),
            rollback=1,
            capture_schema=True,
        )
    )
    assert result.rollback_returncode == 0, result.rollback_output[-1500:]
    assert set(_live_columns(result.schema_after_rollback)) == {"id", "a"}
