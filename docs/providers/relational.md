# PostgreSQL, MySQL, and MariaDB

The relational providers use Testcontainers and SQLAlchemy drivers installed by
the harness dependency groups.

## Shared coverage

The ecommerce schema checks users, orders, and order items. Integration tests
validate table creation, foreign key relationships, unique constraints,
indexes, staged column changes, rollback, reapply, reset, and reverse
engineering.

## PostgreSQL

PostgreSQL is the strict PR smoke provider and the primary relational reference
for release checks. Its tests use the PostgreSQL URL and database inspector.

## MySQL

MySQL uses the PyMySQL driver and its own provider URL. It has an experimental
full-version diff cell for a known released-package reverse-engineering type
issue. Initial migration, evolution, semantic constraints, and generated model
coverage remain executable.

## MariaDB

MariaDB uses a separate image, port, and provider class even though it shares
the PyMySQL driver family. The distinction matters because foreign key and DDL
behavior differs from MySQL. The current PyPI release has an explicit table
ordering XFAIL in generate-models coverage and an experimental matrix cell.
