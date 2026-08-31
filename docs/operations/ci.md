# CI

The harness separates confidence from cost.

## Pull request gate

`.github/workflows/pr-gate.yml` runs locked installation, Ruff, non-integration
smoke tests, a PostgreSQL smoke round trip, and PostgreSQL constraint
semantics. The non-integration job is a complete tier, not a sample: every
SQLite case, including constraint enforcement and regeneration silence, runs
without Docker.

## Backend matrix

`.github/workflows/matrix.yml` runs on schedule or manual dispatch. Its matrix
selects one backend per job and passes the backend selection into pytest. This
prevents a MySQL job from silently running ClickHouse or PostgreSQL work.

Each relational backend also runs the semantics suite, so a job proves the
server enforces what the models declare rather than only that the migration
applied. ClickHouse skips it: it has no `UNIQUE` or `CHECK` table constraints.

PostgreSQL and ClickHouse cells are strict. MySQL and MariaDB experimental
cells are allowed to expose known release failures while preserving their logs
and artifacts; the current findings are listed in
[Known Findings by Release](../known-compatibility.md).

## Plugin workflow

`.github/workflows/plugins.yml` installs and exercises the public plugin path,
including the role lifecycle that `dbwarden-pgsql-rbac` contributes, against a
live PostgreSQL server.

## Distribution workflow

`.github/workflows/distribution.yml` runs package inspection and CLI contract
tests in a clean locked environment.

## Performance workflow

`.github/workflows/performance.yml` runs opt in scale and 500 migration suites.
It stores benchmark JSON as an artifact.

## Local reproduction

Use the exact command shown in the failed workflow step, then set
`DBWARDEN_HARNESS_ARTIFACT_DIR=artifacts` to retain local evidence.
