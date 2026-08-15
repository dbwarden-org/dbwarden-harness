# Safety

Safety tests verify that DBWarden distinguishes harmless changes from changes
that can destroy data or invalidate an application.

## Current checks

- Invalid CLI commands return failure instead of synthetic success.
- Stateful commands fail clearly without consumer configuration.
- Non-destructive schema creation is reported as informational.
- Destructive table removal is blocked without force confirmation.
- The same destructive operation can proceed with explicit force.

## Test boundary

Safety tests use temporary SQLite projects for deterministic command behavior.
Destructive operations are not run against shared or persistent databases.

## Adding a safety case

Add a case when a new operation has a meaningful risk classification. Assert the
blocked invocation, the required confirmation text, the forced invocation, and
the resulting database state where execution is safe.
