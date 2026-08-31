# Known Findings by Release

The integration suite is intentionally strict. Findings are recorded here
rather than being marked as passing or silently skipped when the affected test
is selected.

Each entry names the release it was observed on, the test that observes it, and
the state of the fix. A finding is only removed once a published release passes
the test that found it.

## dbwarden `0.17.1`

Observed with `dbwarden==0.17.1` installed from PyPI.

- **Table constraints are rendered with PostgreSQL syntax on SQLite.** A model
  declaring `uniques` or `checks` generates
  `ALTER TABLE branches ADD CONSTRAINT uq_branches_code UNIQUE (code)`, which
  SQLite cannot parse. `migrate` fails with
  `near "UNIQUE": syntax error`, so the schema cannot be created at all.
  Observed by `suites/semantics/test_constraint_semantics.py`. The core
  checkout emits the constraints inside `CREATE TABLE`.
- **A foreign key blocks generation on SQLite.** A model with a
  `ForeignKey` column fails during `make-migrations` with
  `RollbackContractError: Placeholder rollback for add_foreign_key on <table>
  is not allowed`. The core checkout emits the reference inside `CREATE TABLE`
  and applies cleanly.
- **Configuration-declared objects are recreated on every migration.** The
  PostgreSQL preamble - roles, domains, sequences, functions, triggers,
  composite types, extended statistics, event triggers, default privileges - is
  diffed against a hardcoded empty snapshot instead of the database, so every
  declared object reads as new on every run. Applying the second migration
  fails with `role "..." already exists`, and changing an attribute emits
  `CREATE ROLE` where `ALTER ROLE` was needed. Observed by
  `suites/plugin_integration/test_pgsql_rbac_roles.py` with
  `dbwarden-pgsql-rbac` installed; the core checkout passes the real snapshot.
- **Reverse-engineered models can reference `func` without importing it.** A
  column whose default is `now()` is written as `default=func.now()` while
  `func` is filtered out of the generated import line, so the artifact raises
  `NameError: name 'func' is not defined` when dbwarden loads it. Reached
  through dbwarden's own bookkeeping tables, which the supported flow excludes -
  the generated file is unloadable only when they are included.
- **Integer primary keys are not auto-incrementing on MySQL and MariaDB.** The
  same model that produces `SERIAL` on PostgreSQL and `AUTOINCREMENT` on SQLite
  produces a plain `id INTEGER NOT NULL PRIMARY KEY`, and the first insert that
  omits the key fails with
  `(1364, "Field 'id' doesn't have a default value")`. The migration itself
  applies cleanly, so this surfaces only when a test writes a row.

## dbwarden `0.16.5`

Historical. Retained because the coverage matrix still refers to these cells.

- PostgreSQL ecommerce migrations require `IndexSpec` metadata; SQLAlchemy-only
  `Index` declarations were not emitted, so the reference schemas use the
  public dbwarden metadata form.
- MariaDB migration generation ordered `order_items` before its referenced
  `orders` table, producing a foreign-key creation error.
- MySQL reverse engineering could report an incomplete `varchar` type without a
  length during a final diff.
- The `clickhouse://` URL scheme was not recognized when converting to the
  `clickhousedb` SQLAlchemy dialect, corrupting credentials.
- Reverse-engineered SQLite models reported an informational autoincrement
  drift for implicit integer primary keys.

## Reproduce

```bash
DBWARDEN_HARNESS_RUN_INTEGRATION=1 uv run pytest -m integration suites/semantics
DBWARDEN_HARNESS_RUN_INTEGRATION=1 uv run pytest -m integration suites/round_trip
uv run pytest -q suites/semantics -m "not integration"
```

The last command needs no Docker and reproduces both SQLite findings.

The provider lifecycle matrix is independent of these dbwarden release findings
and passes all declared backend/version cases.
