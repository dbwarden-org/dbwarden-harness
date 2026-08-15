# Known Compatibility Findings

The integration suite is intentionally strict. These findings are not marked
as passing or silently skipped when the affected test is selected.

## DBWarden `0.16.5`

- PostgreSQL ecommerce migrations require `IndexSpec` metadata. SQLAlchemy-only
  `Index` declarations are not emitted by the release; the reference schemas
  use the public DBWarden metadata form.
- PyPI `0.16.5` MariaDB migration generation orders `order_items` before its
  referenced `orders` table, producing a foreign-key creation error. The core
  checkout now topologically orders newly created tables; this is fixed for the
  next release.
- PyPI `0.16.5` does not recognize the `clickhouse://` URL scheme when
  converting to the `clickhousedb` SQLAlchemy dialect, corrupting credentials.
  The core checkout now parses that scheme correctly; this is fixed for the
  next release.
- PyPI `0.16.5` reverse-engineered SQLite models report an informational
  autoincrement drift. The core checkout now treats implicit integer primary
  keys as equivalent; this is fixed for the next release.

Reproduce backend findings with:

```bash
DBWARDEN_HARNESS_RUN_INTEGRATION=1 uv run pytest suites/round_trip/test_backend_round_trip.py -q
```

The provider lifecycle matrix is independent of these DBWarden release
findings and passes all 14 declared backend/version cases.
