# Offline Tests

Not every environment that generates a migration can reach the database that
will receive it. Offline generation reads exported model state instead of a
live server, which makes that state a trusted artifact - and a tampered or
missing artifact must be detected rather than quietly used.

## Files

- `suites/offline/test_sqlite_offline.py`
- `suites/offline/test_data_migrations.py` — declarative data bundles, transitions, merges, tamper detection, and rollback/reapply through the public CLI

## Scenarios

| Test | Question |
| --- | --- |
| `test_sqlite_offline_generation_uses_exported_model_state` | Does `make-migrations --offline` work from exported state alone? |
| `test_offline_model_state_checksum_detects_tampering` | Is an edited state file detected? |
| `test_deleted_model_state_is_recovered_from_applied_migrations` | Can state be rebuilt from applied migrations? |
| `test_offline_generation_reports_absent_state` | Does generation without any state say so instead of inventing a baseline? |

`tools/offline_integrity.py` writes and verifies the manifest the tamper test
compares against.

## Run

```bash
uv run pytest -q suites/offline
```
