# Correctness

The harness defines correctness as evidence that a published DBWarden package
can move a real database between intended schema states and describe the result
accurately.

Correctness is layered:

1. The package installs and exposes the public CLI.
2. The provider starts and reports the expected server version.
3. The migration file is generated and has the expected artifacts.
4. The database accepts and applies the SQL.
5. The resulting state matches the reference schema.
6. Reverse-engineered models can be loaded by a consumer project.
7. Public diff reports no remaining operations.
8. Rollback and reapplication preserve the expected history.

A command exit code is therefore only one assertion in a passing test.

## Correctness documents

- [Convergence Model](convergence.md)
- [Round Trips](round-trips.md)
- [Semantic Drift](semantic-drift.md)
- [Durability and Recovery](durability.md)
- [Safety](safety.md)
- [Offline Integrity](offline-integrity.md)
