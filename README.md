<p align="center">
  <img src="https://raw.githubusercontent.com/dbwarden-org/dbwarden/refs/heads/main/assets/icon.png" alt="DBWarden" width="128"/>
</p>
<p align="center">
  <strong style="font-size: 2.5em;">DBWarden Test Harness</strong>
</p>
<p align="center">
    <em>Release confidence through real databases and public interfaces.</em>
</p>
<p align="center">
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white&style=for-the-badge" alt="Python">
  </a>
  <a href="https://github.com/dbwarden-org/dbwarden-harness/actions">
    <img src="https://img.shields.io/github/actions/workflow/status/dbwarden-org/dbwarden-harness/.github/workflows/pr-gate.yml?branch=main&label=CI&logo=github&style=for-the-badge" alt="CI">
  </a>
  <a href="https://github.com/dbwarden-org/dbwarden-harness">
    <img src="https://img.shields.io/badge/Testing-Black--box-10AC84?style=for-the-badge" alt="Black box testing">
  </a>
  <a href="https://www.docker.com/">
    <img src="https://img.shields.io/badge/Docker-Testcontainers-2496ED?logo=docker&logoColor=white&style=for-the-badge" alt="Docker Testcontainers">
  </a>
</p>

<p align="center">
  <strong><a href="https://dbwarden-org.github.io/dbwarden-harness/">Documentation</a></strong>
  &nbsp;|&nbsp;
  <strong><a href="https://github.com/dbwarden-org/dbwarden-harness">Source Code</a></strong>
  &nbsp;|&nbsp;
  <strong><a href="https://github.com/dbwarden-org/dbwarden">DBWarden</a></strong>
</p>

DBWarden Test Harness is a standalone black-box validation suite for DBWarden
releases, database backends, and plugin combinations. It installs DBWarden as
a consumer, invokes its public command line interface, creates disposable real
database instances, and verifies the resulting schema and migration history.

The harness is not a second unit test suite for DBWarden internals. It is a
release certification boundary. If a published wheel, database driver,
database version, or plugin combination behaves differently from the supported
contract, this repository should expose that difference.

## At a glance

- PyPI and clean wheel installation checks
- Public CLI and artifact contract checks
- PostgreSQL, MySQL, MariaDB, ClickHouse, and SQLite providers
- Multiple database versions through disposable containers
- Real migration application and schema convergence
- Full `generate-models` reverse engineering flows
- Staged upgrade, rollback, reapply, and recovery tests
- Foreign key, unique constraint, index, default, and type assertions
- ClickHouse engine, sorting key, partition, and table metadata checks
- Safety classification and destructive operation checks
- Offline model-state checksum verification
- Plugin discovery and public installation checks
- Alembic, Django, and Atlas adoption fixtures
- Deterministic SQL contract snapshots
- Long migration chain and replay benchmarks
- Failure artifacts with provider logs and release provenance

## Why a Harness?

DBWarden's source repository already contains unit tests, regression tests, SQL
builder tests, handler tests, and current-environment integration tests. Those
tests are necessary, but they cannot answer every question that users have when
they install a released package.

### A source checkout is not a release

Tests executed inside a source checkout can accidentally use local modules,
local plugin code, local package metadata, or development-only dependencies. A
published wheel has a different boundary. Files may be missing, entry points
may be misdeclared, optional dependencies may not resolve, and public imports
may not match the development environment.

The harness installs the package as a consumer would. It records the package
version, installation location, Python runtime, platform, dependency lock
checksum, and plugin versions. A failure can therefore be tied to a specific
artifact instead of an ambiguous working tree.

### A unit test is not a database

SQL text that looks correct can still fail when a real server parses it. A
database may reject a foreign key because the referenced table was created
later. A type accepted by one MySQL release may be rejected by MariaDB. A
ClickHouse engine can require an `ORDER BY` expression that is invisible to a
generic SQLAlchemy inspection.

The harness starts real database servers and applies the generated SQL against
them. This validates the complete path from model declaration to generated
file to driver execution to persisted schema.

### One backend is not every backend

Database support is a matrix, not a boolean. PostgreSQL, MySQL, MariaDB,
ClickHouse, and SQLite differ in types, transactional behavior, metadata
inspection, foreign key rules, identifier handling, and rollback semantics.
Version changes can introduce new behavior without changing DBWarden code.

The provider matrix runs the same consumer flow against declared database
versions. Lifecycle tests prove that a server is ready. Migration tests prove
that DBWarden can use it. The two signals are intentionally kept separate.

### A migration can pass and still drift

A successful migration command proves that the server accepted the statements.
It does not prove that the resulting state matches the intended model. A
generated model can omit a constraint, normalize a type incorrectly, lose a
ClickHouse engine option, or include DBWarden's own bookkeeping tables.

The harness captures semantic state after migration, reverse engineers the
database, reloads the generated models, and runs a public diff. This tests
convergence rather than only command success.

### Upgrade paths matter more than initial creation

An initial schema often hides ordering and compatibility problems. Production
databases evolve through many small migrations. Deployments may roll back a
subset, rerun after an interrupted process, or recover after a failed
statement. Non-transactional engines can leave partial state behind.

The harness includes staged evolution, rollback, reapplication, missing file,
failed migration, and long chain tests. The goal is to validate the history a
user will actually operate, not just the schema a new project creates once.

### Plugins are part of the product surface

Plugins extend DBWarden's public behavior. Discovery can succeed while plugin
composition fails because of ordering, duplicate registrations, optional
dependencies, or version skew.

The harness installs plugins through the public CLI, verifies distribution
metadata, checks discovery, and provides a home for composed integration
scenarios. Core and plugin compatibility can be evaluated together instead of
assuming that independent plugin tests are sufficient.

### Failures must be actionable

Integration failures are expensive to reproduce. A useful failure needs the
exact command, generated migrations, model state, database version, provider
logs, package provenance, and diff output.

The harness collects these artifacts when configured to do so. This turns a
remote CI failure into a reproducible package of evidence instead of a test
name and a truncated traceback.

## What the harness does not do

The harness does not replace DBWarden's internal unit tests. It does not import
private implementation modules, monkey patch database connections, or use
SQLite as a substitute for a PostgreSQL, MySQL, MariaDB, or ClickHouse test.
It does not silently convert a known release defect into a passing result.
Known compatibility cells are explicit, retained in reports, and documented.

## From zero to a release report

The normal certification flow is:

1. Resolve a locked Python environment.
2. Inspect the installed DBWarden distribution and entry points.
3. Install requested plugins through the public interface.
4. Start a pinned disposable database provider.
5. Create a consumer project through the DBWarden CLI.
6. Generate and apply migrations from a reference schema.
7. Capture portable and backend-specific schema state.
8. Reverse engineer the live database with `generate-models`.
9. Reconfigure the project to use the generated models.
10. Run a public diff and require convergence.
11. Apply staged changes, roll them back, and reapply them.
12. Reset the provider and verify isolation.
13. Store reports and failure artifacts.

## Installation

The recommended workflow uses `uv` and the committed lockfile:

```bash
uv venv
uv sync
```

The project requires Python 3.12 or newer. Database drivers and Testcontainers
dependencies are installed by the project configuration.

## Quickstart

Run lint and fast black-box checks:

```bash
uv run ruff check .
uv run pytest -m "not integration and not slow"
```

Integration tests require Docker and are disabled unless explicitly enabled:

```bash
DBWARDEN_HARNESS_RUN_INTEGRATION=1 uv run pytest -m integration suites/round_trip
```

Run reverse engineering coverage across the latest supported providers:

```bash
DBWARDEN_HARNESS_RUN_INTEGRATION=1 uv run pytest -m integration suites/round_trip/test_generate_models_integration.py
```

Run staged evolution and provider reset coverage:

```bash
DBWARDEN_HARNESS_RUN_INTEGRATION=1 uv run pytest -m integration suites/round_trip/test_backend_evolution.py suites/round_trip/test_providers.py
```

Run the full backend matrix manually through GitHub Actions, or run a local
backend selection with `-k`:

```bash
DBWARDEN_HARNESS_RUN_INTEGRATION=1 uv run pytest -m integration suites/round_trip -k postgres
```

## Reference schemas

Reference schemas are deliberately small, deterministic, and reusable across
provider versions.

### Ecommerce

The ecommerce fixture contains users, orders, and order items. It exercises
primary keys, unique values, foreign keys, indexes, comments, relationships,
and dependency ordering.

### Analytics

The analytics fixture contains timestamped events and ClickHouse MergeTree
metadata. It exercises engine selection and sorting key preservation.

### RBAC complex

The RBAC fixture provides a foundation for role, permission, and extension
composition scenarios.

### Edge cases

The edge case fixture is reserved for identifiers, types, expressions, and
declarations likely to expose quoting or deterministic serialization problems.

## Backend providers

Provider implementations live in `infrastructure/providers`.

| Backend | Declared versions | Main fixture |
| --- | --- | --- |
| PostgreSQL | 14, 15, 16, 17 | Ecommerce |
| MySQL | 8.0, 8.4 | Ecommerce |
| MariaDB | 10.11, 11.4 | Ecommerce |
| ClickHouse | 24.3, 26.6 | Analytics |
| SQLite | Local file | Analytics and edge cases |

Each provider owns readiness polling, URL construction, version reporting,
reset behavior, safe diagnostics, log collection, and teardown. A provider
being reachable is not treated as evidence that migrations work.

## Migration and convergence coverage

The harness validates more than a zero exit code. It checks:

- Migration files exist and contain expected artifacts
- Applied history corresponds to migration files
- Tables and columns exist in the live database
- Foreign keys and unique constraints are preserved
- Indexes and defaults are represented correctly
- Backend-specific table metadata survives reverse engineering
- Rollback removes the expected state
- Reapplication restores the expected state
- Generated models can be loaded by a consumer project
- A public diff reports no remaining operations

The generate-models suite excludes DBWarden-owned bookkeeping tables from the
application model path. The generated artifact is still checked for content,
loadability, backend metadata, and convergence.

## Semantic drift checking

`tools/drift_checker.py` captures portable and backend-aware state.

Portable state includes tables, views, columns, types, nullability, defaults,
primary keys, foreign keys, unique constraints, and indexes. ClickHouse state
also includes engine, sorting key, partition key, and primary key metadata.

Drift reports identify the category and object name. They are intended to make
failures understandable without requiring a reader to compare large SQL files
by hand.

## Durability and recovery

Durability suites cover:

- Fifty migration chains
- Subset rollback
- Reapplication after rollback
- Migration file deletion
- Staged schema evolution
- Repair after a failed migration
- Provider reset and isolation
- Final history integrity

SQLite provides a fast deterministic baseline. Provider-backed evolution tests
exercise real PostgreSQL, MySQL, MariaDB, and ClickHouse connections.

## Plugins and adoption

Plugin tests use the public plugin command flow and inspect installed
distribution metadata. The declared plugin set includes PostgreSQL types,
PostgreSQL RBAC, PostgreSQL extensions, ClickHouse RBAC, FastAPI, sandbox, and
seed packages.

Adoption fixtures document handoff patterns for Alembic, Django, and Atlas. The
baseline flow verifies that an existing schema can be recorded without
reapplying its DDL.

## Distribution provenance and artifacts

Set `DBWARDEN_HARNESS_ARTIFACT_DIR` to retain failure evidence. Artifact bundles
include:

- CLI arguments and return code
- Standard output and standard error
- Generated migrations
- DBWarden model state
- Python and platform information
- Installed package versions and locations
- Harness lockfile checksum
- Provider metadata and container logs

This information is especially important when testing a published package,
because a local development checkout may contain fixes that the release does
not yet have.

## Performance

Performance suites measure snapshot capture, scale behavior, migration replay,
reverse engineering, and serialization. The 500 migration benchmark is
intentionally opt in:

```bash
DBWARDEN_HARNESS_RUN_500_MIGRATION=1 uv run pytest suites/performance -s
```

The current core checkout supports deferred snapshot replay for large batches.
The normal per migration snapshot behavior remains the compatibility baseline.

## Continuous integration

The workflows separate fast feedback from expensive certification:

- `pr-gate.yml` runs lint, smoke tests, and a PostgreSQL integration check.
- `matrix.yml` runs backend-specific provider suites on schedule or manually.
- `plugins.yml` checks public plugin installation and discovery.
- `distribution.yml` checks the installed package and CLI contract.
- `performance.yml` runs opt in scale and benchmark suites.

Experimental compatibility cells remain visible in the matrix. Their artifacts
and reasons are retained rather than silently skipping the tests.

## Compatibility findings

The current PyPI `dbwarden` 0.16.5 package has known findings:

- MariaDB migration generation can order a child table before its referenced
  parent table.
- MySQL reverse engineering can report an incomplete `varchar` type during
  final diff in some full version scenarios.
- Default reverse engineering can include DBWarden bookkeeping tables that are
  not appropriate for application model input.

The first two findings remain explicit experimental cells in the backend
matrix. Details and reproduction commands are in
`docs/known-compatibility.md`.

## Repository layout

```text
infrastructure/   Docker providers and lifecycle code
harness/          CLI, distribution, plugin, matrix, and provenance helpers
schemas/          Reference model fixtures
suites/           Integration, durability, safety, offline, adoption, and performance tests
tools/            Migration driving, drift checking, artifacts, reports, and benchmarks
tests/            Harness unit and contract tests
snapshots/        Committed SQL contract baselines
docs/             Compatibility and coverage documentation
```

## Contribution guidelines

New integration tests should use public DBWarden behavior, real disposable
providers, deterministic data, explicit cleanup, and an artifact that explains
why the test belongs at the release boundary. A test that imports a private
DBWarden module belongs in the DBWarden source repository instead.
