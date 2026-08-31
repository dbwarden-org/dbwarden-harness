# Performance Tests

Performance tests measure the harness and dbwarden as a consumer workflow.

## Measurements

- Snapshot capture microbenchmark
- Reference scale fixture
- Snapshot serialization
- 500 migration preparation, replay, diff, and total time
- Optional deferred snapshot replay

## Run small benchmarks

```bash
uv run pytest -q suites/performance/test_snapshot_benchmark.py
```

## Run scale benchmarks

```bash
DBWARDEN_HARNESS_RUN_SCALE=1 uv run pytest suites/performance/test_scale.py -s
```

## Run the 500 migration benchmark

```bash
DBWARDEN_HARNESS_RUN_500_MIGRATION=1 uv run pytest suites/performance/test_convergence_500.py -s
```

The benchmark is opt in because it is intentionally expensive. Results should
be compared on the same Python, filesystem, dbwarden version, and machine
class. The repository baseline is a reference measurement, not a universal SLA.

To assert against a performance baseline (fail if regression detected) instead
of measuring only:

```bash
DBWARDEN_HARNESS_RUN_500_MIGRATION=1 DBWARDEN_HARNESS_ENFORCE_PERFORMANCE=1 \
  uv run pytest suites/performance/test_convergence_500.py -s
```
