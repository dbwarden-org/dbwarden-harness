# SQL Contract Tests

SQL contract tests protect deterministic generated output and approved
baselines.

## Covered behavior

- Repeated generation is deterministic.
- Snapshot files can be captured and compared.
- Unified SQL differences are readable.
- Approved snapshots can be written to a destination.
- The committed baseline manifest matches the committed baselines.

## Baselines are per release

Generated SQL is a contract for one release, not for all time. A backend fix
legitimately changes the bytes - dbwarden `0.17` emits `AUTOINCREMENT` for a
SQLite integer primary key where `0.16` did not - and a baseline captured two
releases ago would report every intentional improvement as a regression.

Baselines therefore live under the version that produced them:

```text
snapshots/
  SHA256SUMS.json
  v0.16.5/sqlite/minimal.sql
  v0.17.1/sqlite/minimal.sql
```

`SnapshotManager.baseline_for` resolves the directory from the installed
dbwarden version, falling back to a `major.minor` series directory for releases
that share one contract. When no baseline exists for the installed version the
comparison is skipped rather than run against a foreign baseline, and the skip
message names the file to approve.

## Approving a new baseline

```python
from pathlib import Path
from tools.snapshot_manager import SnapshotManager

snapshots = Path("snapshots")
# copy the generated migration to snapshots/v<version>/<backend>/<name>.sql first
SnapshotManager().write_manifest(snapshots)
```

Approve deliberately, and only after a round-trip suite has proved the new SQL
applies. An approved baseline records what a release does, not what it should
do.

## Run

```bash
uv run pytest -q suites/sql_contract tests/test_tools.py tests/test_snapshot_manifest.py
```

SQL snapshots are contracts, not substitutes for real database execution.
Round-trip and semantics suites provide the execution proof.
