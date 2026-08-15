# Semantic Drift

`tools/drift_checker.py` provides the harness's backend-aware state comparison.

## Portable fields

- Table names
- View names
- Column names
- Column types
- Nullability
- Defaults
- Index names
- Primary key columns
- Foreign key relationships
- Unique constraint names

## Backend options

The snapshot also stores table options. ClickHouse capture reads `system.tables`
and records engine, sorting key, partition key, and primary key values.

## Drift output

Each difference is represented as a `DriftItem` containing:

- `kind`: the semantic category
- `object_name`: affected table or global object
- `expected`: expected snapshot value
- `actual`: observed snapshot value

This structure is used by tests and can be serialized by higher-level reports.

## Limits

Inspection capabilities differ by SQLAlchemy dialect. The harness does not
pretend that a backend-neutral inspector sees every backend-native object.
When a backend needs a native path, the provider-specific capture code is
explicit and tested separately.
