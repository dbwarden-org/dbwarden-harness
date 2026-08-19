# Harness Coverage Matrix

The matrix separates provider lifecycle coverage from actual dbwarden migration
coverage. A provider being ready is not evidence that migrations converge.

| Area | SQLite | PostgreSQL | MySQL | MariaDB | ClickHouse |
|---|---:|---:|---:|---:|---:|
| Provider lifecycle | yes | yes | yes | yes | yes |
| Initial migration round trip | yes | yes | yes | release-blocked on `0.16.5` | yes |
| Version round trip | local | scheduled | experimental on `0.16.5` | experimental on `0.16.5` | scheduled |
| Structural drift capture | yes | yes | yes | yes | yes |
| Backend table metadata | limited | dialect-dependent | dialect-dependent | dialect-dependent | engine/order/partition keys |
| Staged upgrade/reapply | yes | yes | planned | planned | yes |
| Rollback execution | yes | yes | planned | planned | yes |
| Failure recovery | partial | yes | planned | planned | yes |
| Adversarial scenarios | no | yes | no | no | yes |
| Production lock/perf safety | no | yes | no | no | yes |

## Adversarial Scenarios

Added under `suites/adversarial/` and run against real Docker databases.

**PostgreSQL**

- rename + type change simultaneously
- rename + constraint change
- drop + recreate with same signature
- ambiguous rename detection
- partition changes
- generated columns
- concurrent indexes (transactional contract)
- enum changes

**ClickHouse single-node**

- ORDER BY changes
- PARTITION BY changes
- codec changes
- projection changes
- materialized-view SELECT changes
- MV target changes
- engine recreation with existing data
- engine recreation + rollback
- partially failed recreate

**ClickHouse replicated cluster**

- MergeTree → ReplicatedMergeTree
- ReplicatedMergeTree → ReplicatedReplacingMergeTree
- replicated materialized view
- ON CLUSTER propagation
- Keeper path changes

**Production lock/performance safety**

- PostgreSQL add column under concurrent workload
- PostgreSQL CREATE INDEX lock classification
- ClickHouse add column under concurrent workload
- ClickHouse engine recreation downtime documentation

## Release Findings

The current PyPI `dbwarden==0.16.5` release fails the MariaDB ecommerce round
trip because its generated migration creates a child table before its parent
tables. The harness intentionally keeps this test strict. The current core
checkout contains the table-ordering fix and should be promoted before marking
that cell passing.

## Execution Tiers

- PR: non-integration checks and one PostgreSQL smoke round trip.
- Nightly: all declared backend versions and staged migration suites.
- Release: clean wheel installation, required plugins, all provider versions,
  rollback/recovery, and retained failure artifacts.
