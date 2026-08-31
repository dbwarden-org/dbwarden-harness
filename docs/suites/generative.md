# Generative Suite

The generative suite answers "**which** of hundreds of nearly-identical declarations work?" and which of them dbwarden accepts, migrates, reports success for, and silently does nothing about.

## Why it exists

A scenario-based test writes one migration and asserts the resulting schema. That passes whether the change was applied or ignored, provided the assertion is written against the same model. The generative suite runs every case as a *pair* of model revisions and records whether a migration file was produced at all, so `no-migration` is a distinct, assertable outcome.

## Test files

| File | Question |
|---|---|
| `test_change_matrix.py` | Does changing one property of a table produce a migration? (40 properties) |
| `test_rollback_inversion.py` | Does a migration's rollback invert *that* migration? |
| `test_type_matrix.py` | Does every SQLAlchemy type map to a ClickHouse type, or get refused? |
| `test_engine_matrix.py` | Does every engine builder produce DDL the server accepts, with its arguments intact? |
| `test_field_and_index_matrix.py` | Are column modifiers, skip indexes and projections rendered faithfully and quoted? |
| `test_injection.py` | Can model-supplied text close a DDL statement? |
| `test_object_kinds.py` | Does every declarable object kind (dictionary, role, seed, data op, named collection, view) reach the database? |
| `test_round_trip_clickhouse.py` | Do reverse-engineered models reproduce the same database? |
| `test_discovery_silence.py` | Is an invalid model reported, or silently dropped? |

## Infrastructure

| Module | Role |
|---|---|
| `tools/model_source.py` | Declarative model builders. Changes one line per case so matrices cannot accidentally vary two things. |
| `tools/case_runner.py` | Runs `GenerationCase` objects through init → make-migrations → migrate in parallel. Records all outcomes. |
| `tools/round_trip_driver.py` | Full declare → migrate → generate-models → adopt → diff cycle. |
| `tools/generation_probe.py` | Instruments extraction to recover silently discarded exceptions. |

## Running

```bash
# Reuse a server you already have
DBWARDEN_HARNESS_RUN_INTEGRATION=1 \
DBWARDEN_HARNESS_CLICKHOUSE_URL='clickhouse://default:@localhost:18123/default' \
  uv run pytest suites/generative -q

# Or let the suite start its own container
DBWARDEN_HARNESS_RUN_INTEGRATION=1 uv run pytest suites/generative -q
```

`DBWARDEN_HARNESS_CLICKHOUSE_VERSION` selects the image (default `26.6`). One container serves the whole session; each case gets its own database.

## See also

- [Test Suites Overview](index.md)
- [Coverage Matrix](../coverage-matrix.md)
