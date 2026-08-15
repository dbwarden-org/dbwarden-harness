import os
from pathlib import Path

import pytest

from tools.convergence_benchmark import model_source


def test_benchmark_model_source_has_requested_table_count():
    source = model_source(3)
    assert source.count("class Table") == 3
    assert 'table_0003' in source


def test_benchmark_rejects_non_positive_counts(tmp_path: Path):
    from tools.convergence_benchmark import run_convergence_benchmark

    try:
        run_convergence_benchmark(tmp_path, migration_count=0)
    except ValueError as exc:
        assert "positive" in str(exc)
    else:
        raise AssertionError("non-positive migration count was accepted")


def test_benchmark_can_use_deferred_snapshot_mode(tmp_path: Path, monkeypatch):
    from tools.convergence_benchmark import run_convergence_benchmark

    executable = os.getenv("DBWARDEN_HARNESS_DEFER_EXECUTABLE")
    if not executable:
        pytest.skip("set DBWARDEN_HARNESS_DEFER_EXECUTABLE to a core checkout")
    monkeypatch.setenv("DBWARDEN_HARNESS_DEFER_SNAPSHOTS", "1")
    run_convergence_benchmark(tmp_path, migration_count=3, executable=executable)

    snapshots = tuple(tmp_path.glob("*.schema.json"))
    assert len(snapshots) == 1
