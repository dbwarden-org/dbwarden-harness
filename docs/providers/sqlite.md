# SQLite

SQLite is a first-class dbwarden backend and a first-class harness provider. It
needs no Docker, so it carries the fast tier: public CLI behaviour, offline
flows, long migration chains, baseline handling, table filtering, repair after
a failed migration, and constraint enforcement.

## Provider contract

`SQLiteProvider` answers the same contract as the container providers -
`start`, `stop`, `reset`, `url`, `version`, `diagnostics` - so a suite can mix
it with a server backend without special-casing construction:

```python
from infrastructure.providers import provider_for

provider = provider_for("sqlite", "local")   # version is accepted and ignored
url = provider.start()
```

Constructed without a path, the provider owns a temporary directory and removes
it on `stop`. Pass a `Path` to keep the database file where a test can inspect
it:

```python
from pathlib import Path
from infrastructure.providers import SQLiteProvider

provider = SQLiteProvider(Path(tmp_path) / "app.db")
```

`version()` reports the linked SQLite library version, which is a property of
the Python runtime rather than of a pinned image. It is therefore recorded in
artifacts but not used as a matrix dimension.

## What SQLite can and cannot certify

SQLite is not a substitute for a server-backed test. It cannot certify
PostgreSQL, MySQL, MariaDB, or ClickHouse SQL, and a passing SQLite case never
marks a server cell green in the coverage matrix.

What it does certify is dbwarden's SQLite backend itself, including the parts
no other backend exercises. SQLite has no `ALTER TABLE ... DROP CONSTRAINT`,
so dbwarden reaches those changes by rebuilding the table: create a staging
table with the new shape, copy the rows, drop the original, rename the staging
table over it. That path has to preserve rows, preserve the constraints that
were not part of the change, produce a symmetric rollback, and leave nothing
behind - `suites/semantics/test_constraint_regeneration.py` asserts all four.

## Run

```bash
uv run pytest -q suites/round_trip/test_sqlite_black_box.py
uv run pytest -q suites/durability/test_sqlite_chain.py
uv run pytest -q suites/offline/test_sqlite_offline.py
uv run pytest -q suites/semantics -m "not integration"
```
