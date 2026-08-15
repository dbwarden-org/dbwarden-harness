# Provider Lifecycle

Every provider follows `DatabaseProvider`:

1. Construct the provider with an image or local database path.
2. Start the provider.
3. Poll until the database accepts a real connection or query.
4. Return a consumer connection URL.
5. Reset user objects between scenarios when requested.
6. Collect diagnostics and logs on failure.
7. Stop and dispose the provider in `finally`.

## Why readiness is more than a port

A published Docker port can accept TCP connections while the database is still
initializing users, schemas, or system tables. `DockerDatabaseProvider` polls
the engine through SQLAlchemy. ClickHouse uses its native client because its
HTTP protocol is not represented by a generic SQLAlchemy URL.

## Isolation

Reset tests create a probe table, reset the provider, and verify that the table
is gone. This prevents one scenario from making a later scenario pass or fail
because of leftover state.

## Run lifecycle tests

```bash
DBWARDEN_HARNESS_RUN_INTEGRATION=1 uv run pytest -m integration suites/round_trip/test_providers.py
```
