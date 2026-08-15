# ClickHouse

ClickHouse uses the native `clickhouse_connect` client for readiness, reset,
and semantic capture. Provider URLs use the HTTP protocol and DBWarden is
configured with the ClickHouse database type.

## Analytics fixture

The analytics schema uses a MergeTree engine and an explicit sorting key. The
round-trip suite checks that the engine and sorting key survive migration and
reverse engineering.

## Native metadata

Generic SQLAlchemy inspection is not sufficient for ClickHouse. The drift
checker queries system tables for engine, sorting key, partition key, and
primary key values. This preserves the metadata that determines ClickHouse
storage and query behavior.

## Run

```bash
DBWARDEN_HARNESS_RUN_INTEGRATION=1 uv run pytest -m integration suites/round_trip -k clickhouse
```
