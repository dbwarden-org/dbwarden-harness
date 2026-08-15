# Alembic Adoption Fixture

The adoption path starts with an existing Alembic-managed database schema, runs
`dbwarden generate-models`, creates a DBWarden baseline, and then validates
subsequent model changes through the public CLI.

The executable smoke path creates a pre-existing SQLite table, invokes
`generate-models --single-file`, and verifies the generated public model
artifact. Provider-backed adoption tests should add the same handoff against
PostgreSQL before treating the fixture as production coverage.
