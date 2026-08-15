# Contributing

## Before changing code

Run the fast checks and inspect the current compatibility notes:

```bash
uv run ruff check .
uv run pytest -m "not integration and not slow"
```

Read `docs/known-compatibility.md` before changing an experimental test. A
known release defect should be made more visible and better diagnosed, not
converted into an unconditional skip.

## Test placement

- `tests`: harness unit and contract tests
- `suites/round_trip`: real schema and backend behavior
- `suites/durability`: history, rollback, and recovery
- `suites/safety`: destructive operation controls
- `suites/offline`: state that does not require a live provider
- `suites/distribution`: installed package behavior
- `suites/plugin_integration`: public plugin behavior
- `suites/adoption`: existing schema handoff behavior
- `suites/sql_contract`: deterministic SQL and snapshots
- `suites/performance`: opt in measurement suites

## Commit and review expectations

Keep changes focused. A test description should explain what a user would
experience and why the source repository cannot already prove it. Integration
tests must use real providers and the public dbwarden CLI.

Do not add private dbwarden imports, mocks that replace database connections,
or broad warning suppression. If a behavior is unsupported, document the
limitation and make its test state explicit.

## Documentation

Build the documentation locally before changing navigation or configuration:

```bash
uv run zensical build --clean
```

The navigation is defined in `zensical.toml`. Every path in the navigation must
exist under `docs`.
