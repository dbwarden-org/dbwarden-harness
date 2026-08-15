# Convergence Model

Convergence means that the model declaration, migration history, live database,
and generated model representation agree at the tested semantic level.

## The four states

### Reference state

The reference model fixture is the intended application schema. It is copied
into a temporary consumer project and loaded through the public configuration
path.

### Migration state

`make-migrations` creates versioned SQL files. The harness checks that the
files exist, can be applied, and remain associated with migration history.

### Live state

`DriftChecker` captures tables, columns, constraints, indexes, views, and
backend options from the real database.

### Reverse-engineered state

`generate-models` produces a consumer model artifact. The harness can configure
the project to use that artifact and run a public diff.

## Why semantic comparison

Raw SQL differs between server versions and dialects even when the schema is
equivalent. The checker compares normalized semantic fields rather than
requiring identical SQL text for every backend.

SQL snapshots still exist for deterministic contract checks. Semantic snapshots
answer whether the database is correct. SQL snapshots answer whether generated
output changed unexpectedly.

## What is not normalized away

Backend-specific behavior is not discarded. ClickHouse engine and sorting key
metadata is compared explicitly. Foreign keys, unique constraints, defaults,
and indexes remain visible in relational snapshots.
