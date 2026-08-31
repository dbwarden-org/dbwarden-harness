# Adversarial Tests

Round-trip tests ask whether the ordinary path works. The adversarial suite
asks about the edges that break real deployments: renames that coincide with
type changes, recreations that must preserve data, engine swaps, replicated
DDL, and migrations running under concurrent load.

## Files

- `test_postgres_adversarial.py`
- `test_clickhouse_adversarial.py`
- `test_clickhouse_replicated_adversarial.py`
- `test_lock_and_performance_safety.py`

## Scenarios

**PostgreSQL**; rename with a simultaneous type change, rename with a
constraint change, drop and recreate with the same signature, ambiguous rename
detection, partition changes, generated columns, concurrent index creation and
its transactional contract, and enum changes.

**ClickHouse, single node**; `ORDER BY` and `PARTITION BY` changes, codec and
projection changes, materialized-view `SELECT` and target changes, engine
recreation with existing data, engine recreation followed by rollback, and a
partially failed recreate.

**ClickHouse, replicated**; `MergeTree` to `ReplicatedMergeTree`,
`ReplicatedMergeTree` to `ReplicatedReplacingMergeTree`, replicated
materialized views, `ON CLUSTER` propagation, and Keeper path changes. These
need `ClickHouseClusterProvider`: two servers and one Keeper on a shared Docker
network.

**Lock and performance safety**; adding a column under concurrent workload on
PostgreSQL and ClickHouse, `CREATE INDEX` lock classification, and documented
downtime for ClickHouse engine recreation.

## Strict by intent

These tests assert the behaviour dbwarden should have. When a release does not
meet a contract, the test fails and the gap is recorded in
[Coverage Matrix](../coverage-matrix.md) rather than being weakened into a
passing assertion.

## Run

```bash
DBWARDEN_HARNESS_RUN_INTEGRATION=1 uv run pytest -q suites/adversarial
```
