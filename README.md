# DBWarden Test Harness

Standalone black-box validation for DBWarden releases, database backends, and
plugin combinations.

The harness treats DBWarden as an external product. It installs the published
package, invokes the public command line interface, creates disposable real
database instances, and checks the resulting database state. It is designed to
find release regressions that unit tests inside the DBWarden source repository
cannot detect.

## What This Repository Tests

- Distribution installation from a locked environment
- Public command line behavior and exit statuses
- Generated migration files and SQL contract snapshots
- Schema convergence after migrations are applied
- Reverse engineering through `generate-models`
- Upgrade, rollback, reapply, and failed migration recovery
- Provider startup, readiness, reset, teardown, and version reporting
- PostgreSQL, MySQL, MariaDB, ClickHouse, and SQLite behavior
- Backend version matrices using disposable containers
- Foreign keys, unique constraints, indexes, defaults, and generated models
- ClickHouse engines, sorting keys, partition metadata, and table options
- Safety checks for destructive operations
- Offline model-state checksum handling
- Long migration chains and replay performance
- Plugin discovery and public plugin installation
- Adoption handoffs for Alembic, Django, and Atlas workflows
- Deterministic SQL and committed baseline snapshots
- Failure artifacts containing commands, logs, migrations, and provenance

## Black-Box Boundary

The harness is intentionally separate from the DBWarden source repository.
Tests interact with DBWarden through public behavior only:

- The installed `dbwarden` executable
- Public configuration and metadata APIs used by consumer model fixtures
- Generated migration files
- Generated model files
- Public database state and provider connections

The harness rejects imports of private DBWarden modules. It also records the
installed package location so a local source checkout cannot accidentally be
used in place of the published distribution.

## Quick Start

Create the locked environment and run the fast checks:

```text
uv venv
uv sync
uv run ruff check .
uv run pytest -m "not integration and not slow"
```

Integration tests require Docker and are disabled by default:

```text
DBWARDEN_HARNESS_RUN_INTEGRATION=1 uv run pytest -m integration suites/round_trip
```

Run one backend round trip:

```text
DBWARDEN_HARNESS_RUN_INTEGRATION=1 uv run pytest -m integration suites/round_trip/test_backend_round_trip.py -k postgres
```

Run reverse engineering coverage:

```text
DBWARDEN_HARNESS_RUN_INTEGRATION=1 uv run pytest -m integration suites/round_trip/test_generate_models_integration.py
```

Run the provider evolution and reset tests:

```text
DBWARDEN_HARNESS_RUN_INTEGRATION=1 uv run pytest -m integration suites/round_trip/test_backend_evolution.py suites/round_trip/test_providers.py
```

## Database Providers

Provider implementations live in `infrastructure/providers`.

| Backend | Declared versions | Main fixture |
| --- | --- | --- |
| PostgreSQL | 14, 15, 16, 17 | Ecommerce |
| MySQL | 8.0, 8.4 | Ecommerce |
| MariaDB | 10.11, 11.4 | Ecommerce |
| ClickHouse | 24.3, 26.6 | Analytics |
| SQLite | Local file | Analytics and edge cases |

Every Docker provider is responsible for readiness polling, connection URL
construction, safe diagnostics, container log collection, reset behavior, and
cleanup. Provider lifecycle tests run independently from migration tests so a
container that starts successfully is not mistaken for a backend that can
apply migrations correctly.

## Reference Schemas

Reference schemas are stored in `schemas` and are intentionally small enough to
run repeatedly while still exercising important relationships.

### Ecommerce

Users, orders, and order items cover primary keys, unique email values, foreign
keys, indexes, comments, and dependency ordering.

### Analytics

Events cover timestamps, numeric values, ClickHouse MergeTree metadata, and
sorting keys.

### RBAC Complex

The RBAC fixture provides a home for role and permission integration scenarios.

### Edge Cases

The edge case fixture covers names and declarations that are likely to expose
quoting, deterministic serialization, or type mapping problems.

## Integration Flows

The strongest test flow is:

1. Start a disposable database.
2. Create a consumer DBWarden project through the public CLI.
3. Write a reference model fixture.
4. Generate and apply migrations.
5. Capture semantic database state.
6. Reverse engineer the live schema with `generate-models`.
7. Reconfigure the project to use the generated models.
8. Run a public diff and require convergence.
9. Apply staged changes, roll them back, and reapply them.
10. Reset the provider and verify that user objects are gone.

The generate-models suite excludes DBWarden-owned bookkeeping tables from the
consumer model path. It still verifies that the generated artifact is complete,
loadable, and convergent for the application schema.

## Semantic Drift Checking

`tools/drift_checker.py` captures portable and backend-specific state.

Portable state includes:

- Tables and views
- Column names and details
- Primary keys
- Foreign keys
- Unique constraints
- Index names

ClickHouse state also includes engine, sorting key, partition key, and primary
key metadata. Drift reports identify the semantic category and object name so a
failure can be diagnosed without reading raw SQL first.

## Durability and Recovery

Durability tests cover 50 migration chains, subset rollback, reapplication,
missing migration files, staged schema evolution, and repair after a failed
migration. SQLite provides a fast deterministic baseline. Provider-backed
evolution tests exercise real PostgreSQL, MySQL, MariaDB, and ClickHouse
connections.

## Safety and Offline Checks

Safety tests verify that destructive operations are classified and that force
confirmation is required where expected. Offline checks verify model-state
manifests, checksum changes, missing state, and deterministic local behavior.

## Plugins and Adoption

Plugin tests use the public plugin command flow and inspect installed
distribution metadata. The declared plugin set includes PostgreSQL type, RBAC,
extension, ClickHouse RBAC, FastAPI, sandbox, and seed packages.

Adoption fixtures document handoff patterns for Alembic, Django, and Atlas. The
baseline flow verifies that a pre-existing schema can be recorded without
reapplying its DDL.

## Distribution Provenance

Failure artifacts include:

- CLI arguments and return code
- Standard output and standard error
- Generated migrations
- DBWarden model state
- Python and platform information
- Installed distribution versions and locations
- Harness lockfile checksum
- Provider metadata and container logs

Set `DBWARDEN_HARNESS_ARTIFACT_DIR` to retain these files from failed tests.

## Performance

Performance suites measure snapshot capture, scale behavior, large migration
replay, and serialization. The 500 migration benchmark is intentionally opt-in:

```text
DBWARDEN_HARNESS_RUN_500_MIGRATION=1 uv run pytest suites/performance -s
```

The current core checkout supports deferred snapshot replay for large batches.
The compatibility baseline remains available so an optimization can be
compared with the normal per-migration snapshot behavior.

## CI Workflows

The repository contains separate workflows for different cost and confidence
levels:

- `pr-gate.yml` runs lint, smoke tests, and a PostgreSQL integration check.
- `matrix.yml` runs backend-specific provider suites on schedule or by manual dispatch.
- `plugins.yml` checks public plugin installation and discovery.
- `distribution.yml` verifies the installed package and command line contract.
- `performance.yml` runs opt-in scale and benchmark suites.

Failed provider jobs retain artifacts. Experimental compatibility cells remain
visible and documented rather than being silently skipped.

## Compatibility Findings

The current PyPI `dbwarden` 0.16.5 package has known compatibility findings:

- MariaDB migration generation can order a child table before its referenced
  parent table.
- MySQL reverse engineering can report an incomplete `varchar` type during
  final diff in some full-version scenarios.
- Default reverse engineering can include DBWarden bookkeeping tables that are
  not appropriate for application model input.

The first two findings remain explicit experimental cells in the backend
matrix. Details and reproduction commands are in
`docs/known-compatibility.md`.

## Repository Layout

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

## License and Contribution

Use the issue tracker for compatibility findings, provider failures, and
proposed fixtures. New integration tests should use public DBWarden behavior,
real disposable providers, deterministic data, and explicit cleanup.
