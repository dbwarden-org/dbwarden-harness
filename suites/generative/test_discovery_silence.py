"""An invalid model must be reported, never silently dropped.

``extract_table_from_model`` swallows every exception and returns ``None``, so a
model that fails to extract simply disappears and ``make-migrations`` reports
``No tables found in models`` and exits 0.  Through the public CLI that is
indistinguishable from an empty project, which is precisely why it needs a test:
the user is told they have no models rather than that one of them is invalid.

:class:`~tools.generation_probe.GenerationProbe` re-runs the same command with
the swallowing instrumented so the failure text can name the real cause.
"""
from __future__ import annotations

import pytest

from tools.case_runner import GenerationCase
from tools.generation_probe import GenerationProbe
from tools.model_source import ClickHouseTable, Column_

pytestmark = pytest.mark.integration

# Each of these is a plausible modelling mistake or a documented spelling.
VANISHING_MODELS = {
    # The form used by docs/databases/clickhouse/declaring-tables.md.
    "integer_settings": ClickHouseTable(settings='{"index_granularity": 4096}'),
    "unknown_setting": ClickHouseTable(settings='{"not_a_real_setting": 1}'),
    "primary_key_not_prefix": ClickHouseTable(
        columns=(Column_("id", primary_key=True), Column_("b")),
        order_by='["id","b"]',
        primary_key='["b"]',
    ),
    "empty_order_by": ClickHouseTable(order_by="[]"),
    "ttl_as_string": ClickHouseTable(
        columns=(Column_("id", primary_key=True), Column_("ts", "DateTime")),
        ttl='"ts + toIntervalDay(1)"',
    ),
    "nullable_primary_key": ClickHouseTable(
        primary_key='["id","a"]', column_meta={"a": "nullable=True"}
    ),
}


@pytest.mark.parametrize("name", sorted(VANISHING_MODELS))
def test_invalid_model_is_reported_not_dropped(clickhouse_runner, name):
    table = VANISHING_MODELS[name]
    result = clickhouse_runner.run(
        GenerationCase(f"vanish_{name}", "clickhouse", (table.source(),), apply=False)
    )
    step = result.steps[0]

    if step.generated:
        return  # dbwarden accepted the model; nothing to report.

    swallowed = GenerationProbe(result.work_dir).swallowed_errors("make-migrations", "probe")
    detail = "\n".join(f"    {error}" for error in swallowed) or "    (probe found none)"

    assert step.returncode != 0, (
        f"model {name!r} produced no migration and dbwarden exited 0 reporting "
        f"{'no tables found' if step.reported_no_tables else 'no changes'}. "
        "A user is told they have no models rather than that one is invalid.\n"
        f"The error that was discarded during discovery:\n{detail}"
    )


def test_probe_recovers_the_discarded_exception(clickhouse_runner):
    """The probe itself must work, or the diagnostics above are worthless."""
    table = VANISHING_MODELS["integer_settings"]
    result = clickhouse_runner.run(
        GenerationCase("probe_selftest", "clickhouse", (table.source(),), apply=False)
    )
    if result.steps[0].generated:
        pytest.skip("dbwarden now accepts integer settings; probe self-test is moot")
    swallowed = GenerationProbe(result.work_dir).swallowed_errors("make-migrations", "probe")
    assert swallowed, (
        "make-migrations dropped the table but the probe recovered no exception; "
        "the instrumentation in tools/generation_probe.py needs updating"
    )
