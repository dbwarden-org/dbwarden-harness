from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from tools.convergence_benchmark import ConvergenceBenchmarkResult


@dataclass(frozen=True)
class PerformanceBaseline:
    migration_count: int
    prepare_seconds: float
    migrate_seconds: float
    diff_seconds: float
    total_seconds: float

    @classmethod
    def load(cls, path: Path, migration_count: int) -> PerformanceBaseline:
        values = json.loads(path.read_text(encoding="utf-8"))[str(migration_count)]
        return cls(migration_count=migration_count, **values)

    def assert_within(self, result: ConvergenceBenchmarkResult, tolerance: float = 0.2) -> None:
        if result.migration_count != self.migration_count:
            raise AssertionError(
                f"Benchmark count changed: expected {self.migration_count}, got {result.migration_count}"
            )
        for name in ("prepare_seconds", "migrate_seconds", "diff_seconds", "total_seconds"):
            actual = getattr(result, name)
            expected = getattr(self, name)
            if actual > expected * (1 + tolerance):
                raise AssertionError(
                    f"Performance regression in {name}: {actual:.3f}s > {expected:.3f}s baseline"
                )
