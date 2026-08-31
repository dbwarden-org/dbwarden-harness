# Durability Tests

An initial schema is created once. A production schema is operated for years.
The durability suite exercises the history a user actually accumulates: long
chains, partial rollbacks, replays, deleted files, and repair after a failure.

## Files

- `suites/durability/test_sqlite_chain.py`

## Scenarios

| Test | Question |
| --- | --- |
| `test_sqlite_migration_chain_can_apply_and_rollback` | Does a chain apply and unwind in order? |
| `test_sqlite_fifty_migration_chain_supports_subset_replay` | Can a subset be rolled back and replayed without losing history? |
| `test_applied_migration_file_deletion_is_detected` | Is a missing file for an applied version reported rather than ignored? |
| `test_staged_schema_upgrade_rollback_and_reapply_converges` | Does the schema return to the same state after down and up? |
| `test_failed_migration_can_be_repaired_and_replayed` | Can an operator recover from a statement the server rejected? |

## Why SQLite carries this suite

Durability is about history bookkeeping, not dialect. SQLite makes fifty
migrations cheap and deterministic, so the chain length is realistic rather
than symbolic. Provider-backed evolution, rollback, and reapply for the server
backends live in `suites/round_trip/test_backend_evolution.py`, where the
dialect actually matters.

## Run

```bash
uv run pytest -q suites/durability
```
