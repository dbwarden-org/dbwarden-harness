# Constraint Enforcement

Convergence compares representations. Enforcement asks a different question:
does the database actually refuse what the models forbid?

The two can disagree. A release can drop every declared `uniques` and `checks`
entry on the way from model to SQL, apply the resulting migration without
error, and produce a schema that a reverse-engineering pass then reports as
consistent - because it is consistent, with a model that lost the constraint at
both ends. Nothing in a shape comparison catches that. An `INSERT` does.

## What the harness asserts

For every declared constraint, the semantics suite performs a write the
constraint forbids and requires the server to reject it:

- a duplicate value where a unique constraint was declared
- a row violating a declared check expression

Both must fail on SQLite, PostgreSQL, MySQL, and MariaDB, and must still fail
after an unrelated constraint has been dropped from the same table.

`tools/sql_probe.py` rolls back every probe, so an unexpected success leaves no
row behind to distort a later assertion in the same test.

## Why this belongs at the release boundary

The consequence of a missing constraint is not a failed migration. It is an
application that inserts duplicates for a week, or an `ON CONFLICT` clause with
no constraint to conflict against, failing at runtime on a code path that was
never exercised in staging. That is a defect a consumer discovers in
production, which makes it exactly the class of defect a release gate exists to
find.

## Relationship to regeneration

A schema can also be enforced and still wrong to operate. If the snapshot of
the live database does not describe it the way the models do, the next
`make-migrations` proposes to correct a schema that was never wrong, dropping
and recreating constraints on every deploy. The semantics suite therefore pairs
each enforcement test with a regeneration test: apply, change nothing,
regenerate, and require silence.

See [Semantics Tests](../suites/semantics.md) for the suite layout and how to
run it.
