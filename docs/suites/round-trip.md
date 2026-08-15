# Round Trip Tests

Round-trip tests are the main provider-backed correctness suite.

## Files

- `test_backend_round_trip.py` checks the latest PostgreSQL, MySQL, MariaDB,
  and ClickHouse reference flow.
- `test_version_matrix_round_trip.py` runs the reference flow across declared
  backend versions.
- `test_generate_models_integration.py` checks reverse engineering and reload.
- `test_backend_evolution.py` checks staged changes, rollback, and reapply.
- `test_providers.py` checks lifecycle, version selection, and reset isolation.
- `test_sqlite_black_box.py` checks public SQLite behavior.

## Run one backend

```bash
DBWARDEN_HARNESS_RUN_INTEGRATION=1 uv run pytest -m integration suites/round_trip -k postgres
```

The matrix workflow uses backend selection to prevent every job from starting
every database family.

## What makes a round trip meaningful

The test does not stop after a command returns zero. It inspects tables,
columns, indexes, constraints, backend table options, generated model content,
and public diff output. This catches failures where SQL execution succeeds but
the representation used for the next migration is incomplete.
