# Writing Fixtures

Reference schemas are the main way to add repeatable database behavior. A
schema is data plus a model source file, not a test that knows dbwarden
internals.

## ReferenceSchema contract

`schemas/base.py` defines:

- `name`: stable schema name used in database configuration
- `models_py`: model source path
- `expected_tables`: tables required after migration
- `expected_indexes`: indexes required after migration
- `backend`: default backend family

The registry discovers directories containing `models.py` and `schema.json`.

## Model source rules

- Import only public dbwarden APIs.
- Keep model source deterministic.
- Use metadata types that represent the intended backend behavior.
- Keep the fixture small enough to run across the version matrix.
- Put backend-specific declarations in the model metadata, not in the test.
- Add expected tables and indexes to the schema manifest.

## Integration test rules

An integration test should:

1. Obtain a provider from `provider_for`.
2. Start it inside a `try` and stop it in `finally`.
3. Use `MigrationPlayer` and `SchemaRunner` for public CLI flows.
4. Capture semantic state after applying changes.
5. Assert a user-visible property, not a private function call.
6. Leave enough output for a failed run to be investigated.

## New provider behavior

Add a provider only when it can implement startup, readiness, reset, version,
diagnostics, and teardown. Add lifecycle tests before adding migration tests.
That prevents an unavailable container from appearing as a migration defect.
