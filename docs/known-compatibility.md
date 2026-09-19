# Known Findings by Release

The integration suite is intentionally strict. Findings are recorded here
rather than being marked as passing or silently skipped when the affected test
is selected.

Each entry names the release it was observed on, the test that observes it, and
the state of the fix. A finding is removed when the source under test passes
the test that found it.

## dbwarden `0.19.0`

Tested against the local `../dbwarden` checkout, which the lockfile resolves
through `[tool.uv.sources]`.

### Resolved from `0.17.1`

- **SQLite emits table constraints inside `CREATE TABLE`.** Declared `uniques`
  and `checks` are applied and enforced by the server.
  `suites/semantics/test_constraint_semantics.py` passes on SQLite and on the
  real-server matrix.
- **A foreign key no longer blocks generation on SQLite.** `make-migrations`
  and `migrate` complete.
- **Configuration-declared objects are diffed against the live snapshot.**
  `suites/plugin_integration/test_pgsql_rbac_roles.py` creates, alters, and
  undeclares a role without the second `migrate` failing with `already exists`.
- **Reverse-engineered models import `func`.** Generated files load.
- **MySQL and MariaDB integer primary keys are `AUTO_INCREMENT`.** Migrations
  apply and inserts that omit the key succeed in
  `test_constraints_are_enforced_on_real_servers`.
- **MariaDB creates a valid lock table.** The v2 lock DDL fell back to the
  SQLite templates because `mariadb` was not a dictionary key, so `migrate`
  failed with
  `BLOB/TEXT column 'namespace' used in key specification without a key length`.
  Fixed in the checkout by aliasing the MariaDB templates to MySQL's.
  Observed by `test_constraints_are_enforced_on_real_servers[mariadb-11.4]`.

### Open

None. The findings below were fixed in the checkout and their tests pass:

- **A PostgreSQL identity column also rendered as `SERIAL`.** A model declaring
  `pg.field(identity="always")` on an integer primary key emitted
  `id SERIAL GENERATED ALWAYS AS IDENTITY PRIMARY KEY`, which PostgreSQL
  rejects with `both default and identity specified`. `_postgres_serial_type`
  now hands the base integer type back when the column carries identity
  metadata. Verified by
  `test_postgresql_identity_and_index_sort_round_trip`.
- **MySQL and MariaDB convergence failed on a length-less `varchar`.** The
  snapshot stores the base type and length separately, and the MySQL column
  definition builder received the bare base type. `_snapshot_type_sql`
  reattaches the length, and inherited charset/collation no longer counts as a
  difference. Verified by `test_declared_database_versions_complete_a_round_trip`
  for MySQL 8.0/8.4 and MariaDB 10.11/11.4, and by
  `test_relational_backend_evolution_rolls_back_and_reapplies`.
- **The last migration of a MySQL/MariaDB run was not recorded.** Each DDL
  statement implicitly commits and the bookkeeping `INSERT` opened a
  transaction nothing committed, so a two-migration run showed only the first
  in `history` and re-applying failed with `Duplicate column name`. The run now
  commits after recording. Verified by
  `test_relational_backend_evolution_rolls_back_and_reapplies`.
- **PostgreSQL index sort options were never captured.** `generate-models` and
  the snapshot extractor called `pg_index_column_has_property` with a 0-based
  key for a 1-based function, so every index reported no sorting.
- **`NULLS NOT DISTINCT` was appended after `WHERE`.** PostgreSQL expects it
  before `INCLUDE`/`WHERE`, so the DDL failed to parse.
- **`pg_storage_params`, column `COLLATE`, and `COMPRESSION` were dropped.**
  The model spec excluded them from `pg_table` and the generator never emitted
  them. Verified by
  `test_postgresql_advanced_indexes_and_table_props_round_trip`.

## dbwarden `0.17.1` (superseded)

Observed with `dbwarden==0.17.1` installed from PyPI. All findings below are
fixed in `0.19.0`; the entries are retained as the historical record of what
the release boundary caught.

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
