# SQL Contract Tests

SQL contract tests protect deterministic generated output and approved
baselines.

## Covered behavior

- Repeated generation is deterministic.
- Snapshot files can be captured and compared.
- Unified SQL differences are readable.
- Approved snapshots can be written to a destination.
- Committed baseline manifests remain available for review.

## Run

```bash
uv run pytest -q suites/sql_contract tests/test_tools.py tests/test_snapshot_manifest.py
```

SQL snapshots are contracts, not substitutes for real database execution.
Round-trip suites provide the execution proof.
