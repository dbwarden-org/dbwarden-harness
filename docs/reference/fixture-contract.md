# Fixture Contract

## Reference schema

A reference schema directory contains:

- `models.py`
- `schema.json`
- `README.md`

The registry converts `schema.json` into `ReferenceSchema`. The model source is
copied into a temporary consumer project and loaded by DBWarden's public model
discovery path.

## Migration fixture

Handwritten migration tests use a database directory such as
`migrations/primary`. Files use the DBWarden format with an upgrade section and
a rollback section. The migration player invokes the CLI and never calls an
internal migration executor.

## Expected assertions

Fixtures should assert expected tables and indexes at minimum. Backend-specific
fixtures should also assert relevant semantic options such as ClickHouse engine
and sorting key values.
