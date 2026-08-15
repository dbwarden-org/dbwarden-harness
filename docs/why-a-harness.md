# Why a Harness?

dbwarden's own test suite is the right place for unit tests, internal
regressions, SQL builder assertions, handler coverage, and tests that need
implementation access. The harness exists because those tests cannot certify a
published package as a consumer experiences it.

## The release boundary is real

A source checkout and a built wheel are different products. A checkout can
resolve local modules, local plugins, development dependencies, uncommitted
files, or source-only entry points. A wheel can omit a file, expose a wrong
entry point, resolve a different optional dependency, or package behavior that
does not match the current checkout.

The harness starts from a locked environment and inspects the installed
distribution. Every failure can include the package version, installation
location, Python runtime, platform, and lockfile checksum. This answers the
question that a source test cannot answer: what happens to a user who installs
this exact release?

## A database is not a string comparison

SQL output can look plausible and still fail at execution time. Foreign key
ordering, database-specific type rules, engine requirements, server defaults,
identifier folding, and transaction behavior all belong to the database
server. A mocked connection cannot reproduce those rules.

The harness creates real disposable providers and applies migrations through
the public CLI. The database parses and executes the statements. The harness
then inspects the resulting state through a backend-aware capture path.

## Backend support is a matrix

dbwarden supports several database families with different semantics. A
passing PostgreSQL test does not certify MySQL. A passing MySQL test does not
certify MariaDB. ClickHouse has a different table engine model, and SQLite is
used for local development with its own behavior.

The provider matrix separates lifecycle readiness from migration correctness.
The first proves that a server is running. The second proves that dbwarden can
create, alter, inspect, and converge against it.

## Initial creation hides history problems

Production schemas do not appear in one operation. They accumulate migrations,
rollback attempts, partial deployments, manual baselines, and version history.
The risky behavior is often in the transition between states rather than in
the first `CREATE TABLE` statement.

The harness therefore tests staged upgrades, rollback, reapplication, deleted
migration files, failed migration repair, long chains, and provider reset. The
same reasoning applies to reverse engineering: the generated model must be
usable by a consumer project, not merely present on disk.

## Plugins are part of the public product

Plugins can add model metadata, SQL, commands, entry points, and database
objects. They may work alone and fail when combined. They may also be present
in the source environment but absent from a wheel or incorrectly discovered at
runtime.

The harness installs plugins through the public plugin interface, checks
distribution metadata, and provides integration suites for composition. It
keeps plugin failures attributable to a package and version.

## Correctness needs evidence

An integration failure that says only `test failed` is expensive to investigate.
The harness can retain the command, standard streams, generated migrations,
model state, provider metadata, container logs, package provenance, and runtime
details. This turns a transient CI event into an artifact that can be studied
and reproduced.

## The boundary also protects the harness

The harness must not become a second copy of dbwarden internals. Private imports
make tests coupled to implementation details and can create false confidence.
The black-box boundary test rejects private module references. Public behavior,
generated artifacts, and real database state are the contract.

## What the harness proves

A passing test provides evidence for a specific combination of:

- dbwarden package version
- Python version and platform
- Plugin versions
- Database image and server version
- Reference schema
- Public CLI flow
- Database state comparison mode

It does not claim that every possible schema or every unsupported plugin works.
It makes the tested boundary explicit and records known gaps rather than
silently widening the claim.
