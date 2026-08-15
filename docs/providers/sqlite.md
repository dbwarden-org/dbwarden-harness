# SQLite

SQLite is the fast local provider. It uses a temporary file and does not require
Docker. SQLite tests validate public CLI behavior, offline flows, long chains,
baseline handling, table filtering, and repair after failed migrations.

SQLite is not a substitute for server-backed tests. It cannot certify
PostgreSQL, MySQL, MariaDB, or ClickHouse SQL. Its value is deterministic local
coverage for workflows that do not need a server-specific feature.

## Run

```bash
uv run pytest -q suites/round_trip/test_sqlite_black_box.py
uv run pytest -q suites/durability/test_sqlite_chain.py
uv run pytest -q suites/offline/test_sqlite_offline.py
```
