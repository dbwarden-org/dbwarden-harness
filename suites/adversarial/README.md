# Adversarial migration suite

This suite exercises the dangerous edges of schema evolution that break real
production deployments: renames, destructive recreates, engine swaps on
ClickHouse, replicated DDL, and concurrent load/lock behavior.

Tests follow the same black-box contract as `suites/round_trip/`: migrations are
hand-written SQL files applied through the public `dbwarden` CLI via
`MigrationPlayer`, and structural assertions use `DriftChecker` plus targeted
system-table queries.

## Scenario inventory

### PostgreSQL (`test_postgres_adversarial.py`)

| Scenario | File |
|---|---|
| rename + type change simultaneously | `test_postgres_adversarial.py` |
| rename + constraint change | `test_postgres_adversarial.py` |
| drop + recreate with same signature | `test_postgres_adversarial.py` |
| ambiguous rename | `test_postgres_adversarial.py` |
| partition changes | `test_postgres_adversarial.py` |
| generated columns | `test_postgres_adversarial.py` |
| concurrent indexes | `test_postgres_adversarial.py` |
| enum changes | `test_postgres_adversarial.py` |

### ClickHouse single-node (`test_clickhouse_adversarial.py`)

| Scenario | File |
|---|---|
| ORDER BY changes | `test_clickhouse_adversarial.py` |
| PARTITION BY changes | `test_clickhouse_adversarial.py` |
| codec changes | `test_clickhouse_adversarial.py` |
| projection changes | `test_clickhouse_adversarial.py` |
| materialized-view SELECT changes | `test_clickhouse_adversarial.py` |
| MV target changes | `test_clickhouse_adversarial.py` |
| engine recreation with existing data | `test_clickhouse_adversarial.py` |
| engine recreation + rollback | `test_clickhouse_adversarial.py` |
| partially failed recreate | `test_clickhouse_adversarial.py` |

### ClickHouse replicated cluster (`test_clickhouse_replicated_adversarial.py`)

Requires `ClickHouseClusterProvider` (two `clickhouse-server` replicas + one
`clickhouse-keeper` on a shared Docker network).

| Scenario | File |
|---|---|
| MergeTree → ReplicatedMergeTree | `test_clickhouse_replicated_adversarial.py` |
| ReplicatedMergeTree → ReplicatedReplacingMergeTree | `test_clickhouse_replicated_adversarial.py` |
| replicated materialized view | `test_clickhouse_replicated_adversarial.py` |
| ON CLUSTER propagation | `test_clickhouse_replicated_adversarial.py` |
| Keeper path changes | `test_clickhouse_replicated_adversarial.py` |

### Production lock / performance safety (`test_lock_and_performance_safety.py`)

| Scenario | File |
|---|---|
| PostgreSQL add column under concurrent workload | `test_lock_and_performance_safety.py` |
| PostgreSQL CREATE INDEX lock classification | `test_lock_and_performance_safety.py` |
| ClickHouse add column under concurrent workload | `test_lock_and_performance_safety.py` |
| ClickHouse engine recreation downtime documentation | `test_lock_and_performance_safety.py` |

## Running

```bash
DBWARDEN_HARNESS_RUN_INTEGRATION=1 pytest suites/adversarial -q
```

## Strict contract philosophy

These tests assert the desirable behavior.  If dbwarden does not yet meet a
contract, the test fails and the gap is documented in
`docs/coverage-matrix.md` Release Findings rather than being silently
weakened.
