# Changelog

All notable changes to the dbwarden Test Harness, newest first. The harness has
no tagged releases yet, so changes are grouped by the date they landed on
`main`.

## 2026-09-19

### Changed

- **dbwarden is resolved from the sibling `../dbwarden` checkout.** The
  lockfile points at the source through `[tool.uv.sources]` and the dependency
  floor is raised to `0.19.0`, so the harness exercises the latest source
  instead of the published wheel. `uv sync --no-sources` still resolves PyPI
  for the distribution certification workflow.
- **The compatibility findings are closed.** Every finding recorded against the
  published `0.17.1` wheel is fixed, along with the PostgreSQL identity, index
  sorting, `NULLS NOT DISTINCT`, and storage-parameter findings. See
  [Known Findings by Release](known-compatibility.md).

### Added

- **A `v0.19.0` SQLite SQL contract baseline.** `0.19.0` emits `AUTOINCREMENT`
  for a SQLite integer primary key, so the byte-level contract is approved per
  release. See [SQL Contract Tests](suites/sql-contracts.md).
- **`dbwarden-redis` in the required plugin matrix.**

### Removed

- **A stale strict `xfail` on MariaDB foreign-key ordering.** The `0.16.5` fix
  is in, so the cell now passes.

### Fixed

- **CI checks out `dbwarden-org/dbwarden` alongside the harness.** Every job
  except distribution needs the sibling checkout for the path source;
  distribution certifies the published wheel with `uv sync --locked
  --no-sources`.
- **Ruff findings in the generative suites and tools** are cleared under the
  current ruff version.
