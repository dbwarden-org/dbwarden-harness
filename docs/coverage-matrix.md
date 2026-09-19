# Harness Coverage Matrix

The matrix separates provider lifecycle coverage from actual dbwarden migration
coverage. A provider being ready is not evidence that migrations converge, and
a migration applying is not evidence that the resulting schema constrains
anything.

| Area | SQLite | PostgreSQL | MySQL | MariaDB | ClickHouse |
|---|---:|---:|---:|---:|---:|
| Provider lifecycle | yes | yes | yes | yes | yes |
| Initial migration round trip | yes | yes | yes | yes | yes |
| Version round trip | local | scheduled | scheduled | scheduled | scheduled |
| Structural drift capture | yes | yes | yes | yes | yes |
| Backend table metadata | table options, index DDL | dialect-dependent | dialect-dependent | dialect-dependent | engine/order/partition keys |
| Constraint emission | yes | yes | yes | yes | n/a |
| Constraint enforcement | yes | yes (14, 17) | yes | yes | n/a |
| Regeneration produces nothing | yes | yes (14, 16, 17) | no | no | no |
| Table rebuild preserves data | yes | n/a | n/a | n/a | recreate path |
| Staged upgrade/reapply | yes | yes | planned | planned | yes |
| Rollback execution | yes | yes | planned | planned | yes |
| Failure recovery | partial | yes | planned | planned | yes |
| Plugin objects on a live server | n/a | roles (create/alter) | no | no | no |
| Adversarial scenarios | no | yes | no | no | yes |
| Production lock/perf safety | no | yes | no | no | yes |

Cells reading `no` are gaps in harness coverage, not known defects. Cells
reading `n/a` describe a backend that has no such concept: ClickHouse has no
`UNIQUE` or `CHECK` table constraints, and only SQLite reaches a schema change
through a full table rebuild.

## Semantics

Added under `suites/semantics/`. These tests apply a migration and then write
rows, because a constraint that a catalog reports but the server does not
enforce is indistinguishable at runtime from one that was never created.

- declared `uniques` are named in the generated SQL
- declared `checks` are named in the generated SQL
- a duplicate insert is refused
- an insert violating a check expression is refused
- regenerating from unchanged models produces no migration at all
- dropping one constraint leaves the table's other constraints enforced
- a SQLite table rebuild preserves the table's rows
- reverse-engineered models keep the constraints and still converge

## Plugin composition

`suites/plugin_integration/test_pgsql_rbac_roles.py` installs
`dbwarden-pgsql-rbac`, declares a role through the `pg_roles` configuration key
and walks it through create, alter, and undeclare against PostgreSQL. Plugin
ops only run once a plugin is loaded, which dbwarden's own suite avoids in
order to stay hermetic, so this path exists nowhere else.

## Adversarial Scenarios

Under `suites/adversarial/`, run against real Docker databases.

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

Findings observed against the release under test are listed in
[Known Findings by Release](known-compatibility.md). The harness resolves
`dbwarden` from the sibling `../dbwarden` checkout. On that `0.19.0` source the
SQLite, PostgreSQL, MySQL, and MariaDB round-trip and semantics cells pass:
table constraints are emitted inside `CREATE TABLE`, integer primary keys are
`AUTO_INCREMENT` on MySQL and MariaDB, configuration-declared objects are
diffed against the live snapshot, and PostgreSQL identity, index sorting,
`NULLS NOT DISTINCT`, and storage parameters all round-trip. There are no open
findings.

## Execution Tiers

- PR: non-integration checks, including the full SQLite semantics tier, and one
  PostgreSQL smoke round trip.
- Nightly: all declared backend versions and staged migration suites.
- Release: clean wheel installation, required plugins, all provider versions,
  rollback/recovery, and retained failure artifacts.
