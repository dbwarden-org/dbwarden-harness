# Version Matrix

`harness/matrix.py` declares supported Python and database versions. The
provider matrix test checks that each declared provider starts, reports its
expected version, and resets successfully. The version round-trip suite adds
migration behavior for every declared database version.

## Select cases locally

```bash
DBWARDEN_HARNESS_RUN_INTEGRATION=1 \
DBWARDEN_HARNESS_BACKEND=postgres \
DBWARDEN_HARNESS_VERSIONS=14,17 \
uv run pytest -m integration suites/round_trip/test_providers.py
```

## CI behavior

The scheduled matrix workflow runs backend-specific jobs. PostgreSQL and
ClickHouse are currently strict. MySQL and MariaDB cells run every declared
case and upload artifacts; their earlier compatibility findings are fixed on
the `0.19.0` source the harness resolves.
