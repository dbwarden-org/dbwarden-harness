from pathlib import Path

import pytest

from tools.convergence_benchmark import ConvergenceBenchmarkResult
from tools.performance_baseline import PerformanceBaseline


def test_performance_baseline_accepts_measurement_within_tolerance():
    baseline = PerformanceBaseline(3, 1.0, 2.0, 3.0, 6.0)
    result = ConvergenceBenchmarkResult(3, 1.1, 2.1, 3.1, 6.1)

    baseline.assert_within(result)


def test_performance_baseline_rejects_regression():
    baseline = PerformanceBaseline(3, 1.0, 2.0, 3.0, 6.0)
    result = ConvergenceBenchmarkResult(3, 1.0, 2.5, 3.0, 6.5)

    with pytest.raises(AssertionError, match="migrate_seconds"):
        baseline.assert_within(result)


def test_performance_baseline_loads_versioned_json():
    path = Path(__file__).parents[1] / "baselines" / "performance.json"

    baseline = PerformanceBaseline.load(path, 500)

    assert baseline.total_seconds == 300.3
