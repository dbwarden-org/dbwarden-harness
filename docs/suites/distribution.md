# Distribution Tests

Distribution tests treat the installed wheel as the product under test.

## Covered behavior

- dbwarden package metadata can be inspected.
- Expected package files are present.
- The `dbwarden` console entry point exists.
- Development files are not leaked into the distribution.
- The public CLI exposes core commands.
- The public CLI reports a version.
- A clean installed distribution is not resolved from a source checkout.
- Provenance records package locations and versions.

## Run

```bash
uv run pytest -q tests/test_distribution.py tests/test_distribution_smoke.py
uv run pytest -q suites/distribution
```

The distribution workflow installs the locked harness environment and runs
these checks in GitHub Actions.
