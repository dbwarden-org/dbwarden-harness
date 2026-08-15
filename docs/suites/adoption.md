# Adoption Tests

Adoption tests cover the handoff from an existing schema or external migration
tool to DBWarden.

## Fixtures

Documentation fixtures exist for:

- Alembic
- Django
- Atlas

Each fixture explains a public `generate-models` and baseline workflow.

## Current executable checks

- An existing SQLite schema can be reverse engineered.
- A generated model file is written to the requested output directory.
- Existing schemas can be marked as baseline without reapplying DDL.
- All three handoff fixture documents contain baseline and schema guidance.

## Run

```bash
uv run pytest -q suites/adoption
```

The current executable baseline uses SQLite. Actual Django, Atlas, and Alembic
tool execution requires those external tools and is intentionally not claimed
by the current suite.
