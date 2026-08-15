# Durability and Recovery

Migration durability is about behavior after history becomes nontrivial or
execution becomes imperfect.

## Covered scenarios

- A 50 migration SQLite chain
- Applying and rolling back a subset
- Reapplying previously rolled back migrations
- Detecting deleted applied migration files
- Staged relational schema changes
- ClickHouse column evolution
- Repairing a failed SQLite migration and rerunning it
- Resetting real providers after applied objects exist

## Why failure tests matter

Relational databases can execute DDL under different transactional rules.
MySQL, MariaDB, and ClickHouse can leave different partial states than
PostgreSQL or SQLite. A migration runner must report the failure accurately and
leave a state that can be diagnosed and repaired.

## Current boundary

The current recovery test covers repair and replay on SQLite. Provider-backed
evolution and reset tests cover real database state. Process termination,
concurrent lock contention, and partial failure injection remain separate
areas for future provider-specific suites.
