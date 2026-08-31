# Semantics Tests

Structure is not behaviour. A migration can apply cleanly, and the catalog can
report the object, while the database still accepts rows the models forbid.

The semantics suite declares constraints through the public model API, applies
the generated migration to a real server, and then tries to violate them.

## Files

- `test_constraint_semantics.py` checks that declared `uniques` and `checks`
  reach the server and that the server enforces them.
- `test_constraint_regeneration.py` checks that an applied schema stays
  converged, and that dropping one constraint touches only that constraint.

## Why enforcement and not inspection

A constraint recorded in a catalog but not enforced is indistinguishable at
runtime from one that was never created. Inspection cannot tell those apart;
an `INSERT` can. Each assertion states what it expects the database to refuse
and why:

```python
probe.assert_rejects(
    "INSERT INTO branches (code) VALUES ('north')",
    because="uq_branches_code makes branches.code unique",
)
```

`tools/sql_probe.py` always rolls back, so a statement that unexpectedly
succeeds leaves no row behind to confuse a later assertion.

## Why regenerating must produce nothing

The expensive failure here is not a broken migration, it is a confident one.
If the snapshot of a live database does not describe it the way the models do,
every later `make-migrations` proposes to "fix" a schema that was never wrong:
dropping and recreating a unique constraint, rebuilding every foreign key and
index, or rewriting a column's storage. Each run applies cleanly, so nothing
fails. The schema just churns, holding locks, on every deploy.

`test_unchanged_models_regenerate_nothing_on_postgres` is parametrized by
server version on purpose. Catalog columns and their defaults move between
major versions, so a snapshot query that quietly returns nothing on one of them
produces churn on exactly that version and no other.

## Run

```bash
uv run pytest -q suites/semantics -m "not integration"
DBWARDEN_HARNESS_RUN_INTEGRATION=1 uv run pytest -m integration suites/semantics
```

The SQLite cases run in the fast tier because they need no container. The
PostgreSQL, MySQL, and MariaDB cases carry the `integration` marker.
