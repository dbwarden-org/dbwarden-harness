# Database Providers

Providers give integration tests real, disposable database instances. They
are deliberately separate from the migration assertions so startup failures,
server readiness failures, and DBWarden failures can be distinguished.

## Declared versions

| Backend | Versions |
| --- | --- |
| PostgreSQL | 14, 15, 16, 17 |
| MySQL | 8.0, 8.4 |
| MariaDB | 10.11, 11.4 |
| ClickHouse | 24.3, 26.6 |
| SQLite | Local file |

See [Provider Lifecycle](lifecycle.md) for startup guarantees and
[Version Matrix](version-matrix.md) for selection behavior.
