# Architecture

The harness is organized around a small number of consumer-facing abstractions.

## Test process

Tests invoke the installed `dbwarden` command through
`harness/cli.py`. The runner captures output, return codes, timeouts, and the
working directory. It does not import dbwarden implementation modules.

## MigrationPlayer

`tools/migration_player.py` owns the public CLI workflow for a temporary
consumer project. It can initialize a project, write model source, configure a
database, create migrations, migrate, roll back, inspect status, generate
models, export models, inspect impact, and parse JSON diff output.

The player deliberately works with files and subprocesses. This ensures that
the test follows the same boundary as an application repository.

## SchemaRunner

`tools/schema_runner.py` combines a `ReferenceSchema` with a
`MigrationPlayer`. It prepares model source, configures the database, applies a
baseline, captures state, and runs reverse-engineering flows.

## DatabaseProvider

`infrastructure/providers/base.py` defines the lifecycle contract:

- `start` starts the provider and returns a URL.
- `stop` disposes the provider.
- `reset` removes user objects while keeping the provider available.
- `version` reports the declared server version.
- `diagnostics` returns safe metadata for artifacts.
- `logs` returns provider logs when available.

Docker providers implement readiness polling against the database engine, not
only the published port.

## DriftChecker

`tools/drift_checker.py` captures a semantic `SchemaSnapshot`. SQLAlchemy
inspection is used for relational databases. ClickHouse uses its public client
and system tables because its HTTP URL is not a generic SQLAlchemy URL.

The snapshot model compares tables, views, columns, constraints, indexes, and
backend table options. The comparison reports a `DriftItem` with a category,
object name, expected value, and actual value.

## SqlProbe

`tools/sql_probe.py` runs ordinary SQL against a live database to test
behaviour rather than shape. `assert_rejects` states the write it expects the
server to refuse and why; every probe rolls back, so a statement that
unexpectedly succeeds leaves no row behind. Inspection can only report that a
constraint exists - a probe reports whether it is enforced.

## CaseRunner

`tools/case_runner.py` runs `GenerationCase` objects (lists of model revisions)
through `init → make-migrations → migrate` in parallel, one database per case.
It records generated SQL, CLI streams, server acceptance, live schema, executed
rollback, and both diffs. Used by the generative matrix suite to assert over
the distribution of results rather than individual scenarios.

## RoundTripDriver

`tools/round_trip_driver.py` executes the full `declare → migrate →
generate-models → adopt → diff + make-migrations` cycle. Reports convergence,
unimportable generated modules, and bookkeeping-table leakage.

## SnapshotManager

`tools/snapshot_manager.py` manages versioned SQL contract baselines. Resolves
the approved baseline for a specific dbwarden release, enabling per-version
comparison rather than hardcoded references.

## GenerationProbe

`tools/generation_probe.py` re-runs a command with
`extract_table_from_model` instrumented, recovering exceptions that
`except Exception: return None` discards. Used only to explain a failure, never
to make one pass.

## ModelSource

`tools/model_source.py` provides declarative model builders for matrix tests.
`ClickHouseTable(...).with_(settings=...)` changes one line of the emitted
module, so a matrix case cannot accidentally vary two things at once.

## OfflineIntegrity

`tools/offline_integrity.py` manages state manifest checksums for offline
integrity verification.

## ArtifactCollector

`tools/artifacts.py` writes command output, metadata, generated files, runtime
information, and provenance. The pytest failure hook also copies temporary work
directories and provider diagnostics when a provider fixture is available.

## Black-box enforcement

`tests/test_black_box_boundary.py` scans harness source for private dbwarden
imports. `harness/provenance.py` checks that installed dbwarden is not resolved
from the harness or product source checkout.
