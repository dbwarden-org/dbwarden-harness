# Harness Coverage Matrix

The matrix separates provider lifecycle coverage from actual DBWarden migration
coverage. A provider being ready is not evidence that migrations converge.

| Area | SQLite | PostgreSQL | MySQL | MariaDB | ClickHouse |
|---|---:|---:|---:|---:|---:|
| Provider lifecycle | yes | yes | yes | yes | yes |
| Initial migration round trip | yes | yes | yes | release-blocked on `0.16.5` | yes |
| Version round trip | local | scheduled | scheduled | scheduled | scheduled |
| Structural drift capture | yes | yes | yes | yes | yes |
| Backend table metadata | limited | dialect-dependent | dialect-dependent | dialect-dependent | engine/order/partition keys |
| Staged upgrade/reapply | yes | planned | planned | planned | planned |
| Rollback execution | yes | planned | planned | planned | planned |
| Failure recovery | partial | planned | planned | planned | planned |

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
