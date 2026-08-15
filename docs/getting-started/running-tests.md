# Running Tests

## Fast checks

Run these checks before changing integration code:

```bash
uv run ruff check .
uv run pytest -m "not integration and not slow"
```

The suite includes harness unit tests, distribution checks, schema registry
checks, artifact tests, parser tests, offline checks, and non-container
durability baselines.

## All non-container tests

```bash
uv run pytest tests suites -m "not integration"
```

The performance benchmark test is small by default. The 500 migration and
scale tests require their explicit environment variables.

## Integration tests

```bash
DBWARDEN_HARNESS_RUN_INTEGRATION=1 uv run pytest -m integration
```

Run one suite while developing:

```bash
DBWARDEN_HARNESS_RUN_INTEGRATION=1 uv run pytest -q suites/round_trip/test_generate_models_integration.py
```

Use `-k` to select a backend. The backend matrix uses this same mechanism to
avoid starting unrelated containers in each job:

```bash
DBWARDEN_HARNESS_RUN_INTEGRATION=1 uv run pytest -m integration suites/round_trip -k clickhouse
```

## Select provider versions

The provider lifecycle suite supports `DBWARDEN_HARNESS_BACKEND` and
`DBWARDEN_HARNESS_VERSIONS`:

```bash
DBWARDEN_HARNESS_RUN_INTEGRATION=1 \
DBWARDEN_HARNESS_BACKEND=postgres \
DBWARDEN_HARNESS_VERSIONS=14,17 \
uv run pytest -m integration suites/round_trip/test_providers.py
```

## Slow suites

```bash
DBWARDEN_HARNESS_RUN_SCALE=1 uv run pytest -m slow suites/performance
```

The 500 migration benchmark is opt in:

```bash
DBWARDEN_HARNESS_RUN_500_MIGRATION=1 uv run pytest suites/performance/test_convergence_500.py -s
```

## Artifacts

```bash
DBWARDEN_HARNESS_ARTIFACT_DIR=artifacts \
DBWARDEN_HARNESS_RUN_INTEGRATION=1 \
uv run pytest -m integration suites/round_trip
```

On failure, the artifact directory contains command output, temporary project
files, generated migrations, model state, provenance, and provider logs when
the provider is available to the pytest hook.
