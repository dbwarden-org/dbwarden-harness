import os
from pathlib import Path

import pytest

from tools.convergence_benchmark import run_convergence_benchmark
from tools.performance_baseline import PerformanceBaseline


@pytest.mark.slow
def test_500_migration_convergence_gate_performance(tmp_path: Path):
    if os.getenv("DBWARDEN_HARNESS_RUN_500_MIGRATION") != "1":
        pytest.skip("set DBWARDEN_HARNESS_RUN_500_MIGRATION=1 to run the 500-migration benchmark")
    result = run_convergence_benchmark(tmp_path, migration_count=500)
    assert result.total_seconds > 0
    artifact_dir = Path(os.getenv("DBWARDEN_HARNESS_ARTIFACT_DIR", str(tmp_path)))
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "convergence-500.json").write_text(result.to_json(), encoding="utf-8")
    if os.getenv("DBWARDEN_HARNESS_ENFORCE_PERFORMANCE") == "1":
        baseline = PerformanceBaseline.load(
            Path(__file__).parents[2] / "baselines" / "performance.json", 500
        )
        baseline.assert_within(result)
