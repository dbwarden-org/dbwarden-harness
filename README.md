# DBWarden Test Harness

Standalone black-box validation for DBWarden releases and plugin combinations.

The harness installs DBWarden from PyPI, invokes its CLI as a consumer, and
uses real database providers for integration suites. It must not import
`dbwarden._internal` or rely on source checkouts.

## Quick Start

```bash
uv venv
uv sync
uv run pytest
```

The initial smoke suite validates the installed distribution and the public
CLI orchestration layer. Testcontainers-backed suites are enabled as providers
and fixtures are added.

Run Docker-backed provider suites explicitly:

```bash
DBWARDEN_HARNESS_RUN_INTEGRATION=1 uv run pytest suites/round_trip
```

The integration marker is skipped by default so contributors can run the
distribution smoke suite without a Docker daemon.

## 500-Migration Benchmark

The performance suite measures preparation, full migration replay, and final
schema diff separately. The local reference measurement on 2026-08-14 was:

| Executable | Replay | Diff | Total |
|---|---:|---:|---:|
| Current core checkout | 274.1s | 6.0s | 282.3s |
| PyPI `0.16.5` | 291.8s | 6.7s | 300.3s |

The current core checkout supports the optimized bulk path with
`DBWARDEN_HARNESS_DEFER_SNAPSHOTS=1`; the same 500-migration workload measured
`10.4s` replay and `18.3s` total when only the final schema snapshot was
written. The default benchmark remains per-migration to preserve the release
baseline.

Run the benchmark explicitly because it is intentionally expensive:

```bash
DBWARDEN_HARNESS_RUN_500_MIGRATION=1 uv run pytest \
  suites/performance/test_convergence_500.py -s
```

The benchmark uses SQLite for repeatability. Provider-backed convergence tests
are required before using these numbers as a production-backend budget.

## Structure

- `infrastructure/providers/`: database lifecycle abstractions
- `schemas/`: reference schema metadata and fixtures
- `suites/`: black-box test suites
- `tools/`: CLI orchestration, drift, and snapshot utilities
- `snapshots/`: committed SQL contract baselines
- `docs/`: harness-specific notes

The complete architectural specification is stored at
`~/Documents/dbwarden-test-harness-spec.md`.

Current integration findings are recorded in `docs/known-compatibility.md`.
Coverage tiers are documented in `docs/coverage-matrix.md`.

Set `DBWARDEN_HARNESS_ARTIFACT_DIR` to persist failed-test command output,
generated migrations, model state, provider diagnostics, and container logs.
