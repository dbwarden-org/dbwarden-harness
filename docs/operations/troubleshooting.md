# Troubleshooting

## Integration tests are skipped

Set the integration switch:

```bash
DBWARDEN_HARNESS_RUN_INTEGRATION=1 uv run pytest -m integration
```

Then confirm Docker is available with `docker info`.

## Provider readiness times out

Check Docker resource limits, image download progress, and the provider image
version. Run the provider lifecycle test with artifacts enabled. The provider
waits for a real database query, so a slow first boot can exceed the default
readiness window.

## A diff reports an SQLAlchemy dialect error

Confirm that the provider URL and database type agree. ClickHouse uses its
native HTTP client for drift capture. Relational providers use SQLAlchemy
drivers supplied by the harness extras.

## A migration fails with a foreign key error

Inspect the generated migration in the artifact bundle. Check table creation
order and compare the failure with `docs/known-compatibility.md`. Do not change
the fixture to hide a real release defect.

## Generated models fail to reload

Inspect `generated/models.py` and `provenance.json`. Confirm that dbwarden-owned
tables were excluded from application model input and that the generated file
uses only public installed APIs.

## Tests pass locally but fail in CI

Compare Python version, dbwarden version, provider image, lockfile digest, and
Docker architecture from the artifact bundle. The harness deliberately records
these values because release and environment differences are common causes.
