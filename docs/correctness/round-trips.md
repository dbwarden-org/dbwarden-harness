# Round Trips

Round-trip tests validate the complete consumer path instead of a single
operation.

## Baseline round trip

The latest backend suite:

1. Starts a provider.
2. Initializes a temporary project.
3. Writes the reference schema models.
4. Generates and applies the initial migration.
5. Captures expected tables and indexes.
6. Captures backend semantic metadata.

The suite covers PostgreSQL, MySQL, MariaDB, and ClickHouse. SQLite has a
separate public CLI and reference schema suite.

## Generate-models round trip

The reverse-engineering suite:

1. Applies the reference schema to a real provider.
2. Runs `generate-models`.
3. Verifies that the generated file contains the application tables.
4. Excludes dbwarden-owned bookkeeping tables from application model input.
5. Enables ClickHouse engine metadata where appropriate.
6. Reloads the generated file through dbwarden.
7. Runs public diff and requires convergence.

The test also exercises SQLite table filtering. MariaDB has a strict XFAIL for
the known release table-ordering issue, so a future fixed release produces an
unexpected pass and requires a deliberate review.

## Evolution round trip

The evolution suite creates a table, adds a column, rolls the change back, and
reapplies it. ClickHouse uses an explicit MergeTree table and checks that engine
metadata remains present while columns change.
