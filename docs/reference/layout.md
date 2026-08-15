# Repository Layout

```text
.github/workflows/       Pull request, matrix, plugin, distribution, performance CI
harness/                 CLI, distribution, plugin, matrix, provenance helpers
infrastructure/          Provider abstractions and Docker compose files
schemas/                 Reference model fixtures and registry
suites/                  Black-box test categories
tests/                   Harness unit and contract tests
tools/                   Migration player, drift checker, artifacts, reports, benchmarks
snapshots/               Committed SQL baselines
baselines/               Performance reference data
docs/                    This documentation site
zensical.toml            Documentation configuration and navigation
```

The harness repository is independent of the dbwarden source repository. A
clean harness install resolves dbwarden from the configured distribution
environment.
