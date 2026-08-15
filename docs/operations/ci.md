# CI

The harness separates confidence from cost.

## Pull request gate

`.github/workflows/pr-gate.yml` runs locked installation, Ruff, non-integration
smoke tests, and a PostgreSQL smoke round trip.

## Backend matrix

`.github/workflows/matrix.yml` runs on schedule or manual dispatch. Its matrix
selects one backend per job and passes the backend selection into pytest. This
prevents a MySQL job from silently running ClickHouse or PostgreSQL work.

PostgreSQL and ClickHouse cells are strict. MySQL and MariaDB experimental
cells are allowed to expose known PyPI 0.16.5 failures, while preserving their
logs and artifacts.

## Plugin workflow

`.github/workflows/plugins.yml` installs and exercises the public plugin path.

## Distribution workflow

`.github/workflows/distribution.yml` runs package inspection and CLI contract
tests in a clean locked environment.

## Performance workflow

`.github/workflows/performance.yml` runs opt in scale and 500 migration suites.
It stores benchmark JSON as an artifact.

## Local reproduction

Use the exact command shown in the failed workflow step, then set
`DBWARDEN_HARNESS_ARTIFACT_DIR=artifacts` to retain local evidence.
