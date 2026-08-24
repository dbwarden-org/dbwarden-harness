# Generative matrix suite

The other suites answer "does this scenario work?".  This one answers
"**which** of these hundreds of nearly-identical declarations work?" — and,
just as importantly, which of them dbwarden accepts, migrates, reports success
for, and silently does nothing about.

That last outcome is the one a scenario-based suite cannot see.  A test that
writes one migration and asserts the resulting schema will pass whether the
change was applied or ignored, provided the assertion is written against the
same model.  Here every case is run as a *pair* of model revisions and the
runner records whether a migration file was produced at all, so
`no-migration` is a distinct, assertable outcome.

## Layout

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
| `tools/model_source.py` | Declarative model builders. `ClickHouseTable(...).with_(settings=...)` changes one line of the emitted module, so a matrix case cannot accidentally vary two things at once. |
| `tools/case_runner.py` | Runs a `GenerationCase` (a list of model revisions) through `init → make-migrations → migrate`, in parallel, one database per case. Records generated SQL, CLI streams, server acceptance, live schema, executed rollback and both diffs. Asserts nothing; suites classify via `CaseResult.verdict()`. |
| `tools/round_trip_driver.py` | `declare → migrate → generate-models → adopt → diff + make-migrations`. Reports convergence, unimportable generated modules (by actually importing them in a subprocess) and bookkeeping-table leakage. |
| `tools/generation_probe.py` | Re-runs a command with `extract_table_from_model` instrumented, recovering the exception that `except Exception: return None` discards. Used only to explain a failure, never to make one pass. |

### Why a separate runner rather than `MigrationPlayer`

`MigrationPlayer` drives one project through one flow and raises on the first
unexpected stream — exactly right for a scenario test.  A matrix needs the
opposite: hundreds of projects, no exceptions, and every outcome recorded so the
suite can assert over the *distribution* of results ("40 of 40 changes produced
nothing") instead of one at a time.  `CaseRunner` is built on the same
`DbwardenCli` public-CLI boundary and adds no privileged access.

`GenerationProbe` is the single exception to the black-box rule.  It exists
because "dbwarden exited 0 and said you have no models" is genuinely
indistinguishable from an empty project at the CLI boundary, and a harness that
cannot tell those apart cannot describe the bug.  It only observes.

## Running

```bash
# Reuse a server you already have (fast; no testcontainers needed)
DBWARDEN_HARNESS_RUN_INTEGRATION=1 \
DBWARDEN_HARNESS_CLICKHOUSE_URL='clickhouse://default:@localhost:18123/default' \
  pytest suites/generative -q

# Or let the suite start its own container for the session
DBWARDEN_HARNESS_RUN_INTEGRATION=1 pytest suites/generative -q
```

`DBWARDEN_HARNESS_CLICKHOUSE_VERSION` selects the image (default `26.6`).
One container serves the whole session; each case gets its own database, so the
matrices parallelise without contending for a schema.

## Strict contract philosophy

Same as `suites/adversarial/`: these tests assert the desirable behavior.  A
failure is a documented gap, not a test to weaken.  Where a matrix would
otherwise fail uniformly and say nothing, it includes **contrast cases** that are
expected to pass — a single migration adding three columns inverts correctly
(`test_rollback_inversion.py`), identifier and comment escaping holds
(`test_injection.py`), `ADD COLUMN` renders every modifier the change matrix
refuses to alter (`test_change_matrix.py`).  Those keep the suite honest: if the
contrast cases also start failing, the harness is broken, not dbwarden.
