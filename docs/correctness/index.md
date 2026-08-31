# Correctness

The harness defines correctness as evidence that a published dbwarden package
can move a real database between intended schema states and describe the result
accurately.

Correctness is layered:

1. The package installs and exposes the public CLI.
2. The provider starts and reports the expected server version.
3. The migration file is generated and has the expected artifacts.
4. The database accepts and applies the SQL.
5. The resulting state matches the reference schema.
6. The server enforces the constraints the models declared.
7. Reverse-engineered models can be loaded by a consumer project.
8. Public diff reports no remaining operations.
9. Regenerating from unchanged models produces nothing at all.
10. Rollback and reapplication preserve the expected history.

A command exit code is therefore only one assertion in a passing test.

Steps 6 and 9 are the two a shape comparison cannot reach. A schema can match
the reference and still accept rows the models forbid, and it can be correct
and still be rewritten on every deploy.

## Correctness documents

- [Convergence Model](convergence.md)
- [Round Trips](round-trips.md)
- [Constraint Enforcement](enforcement.md)
- [Semantic Drift](semantic-drift.md)
- [Durability and Recovery](durability.md)
- [Safety](safety.md)
- [Offline Integrity](offline-integrity.md)
