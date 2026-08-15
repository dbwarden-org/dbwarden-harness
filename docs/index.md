# DBWarden Test Harness

The DBWarden Test Harness is the release boundary between DBWarden development
and DBWarden consumption.

It installs DBWarden as an external package, invokes public commands, runs
against real disposable databases, and checks the resulting state. The harness
is intentionally separate from the DBWarden source repository because source
tests and consumer tests answer different questions.

## Start here

- Read [Why a Harness?](why-a-harness.md) for the design rationale.
- Follow [Setup](getting-started/setup.md) to install the locked environment.
- Use [Running Tests](getting-started/running-tests.md) for local and CI commands.
- Read [Correctness](correctness/index.md) to understand what a passing test means.
- Check [Compatibility Findings](operations/compatibility.md) before interpreting an experimental failure.

## What is validated

The harness validates distribution installation, public CLI behavior, migration
application, rollback, reverse engineering, semantic convergence, provider
isolation, plugin discovery, adoption flows, offline state, and performance.

The primary unit of confidence is not a generated SQL string. It is a complete
consumer flow that produces the expected live database state and can explain
why it passed or failed.

## Repository

The source repository is available at
[dbwarden-org/dbwarden-harness](https://github.com/dbwarden-org/dbwarden-harness).

The product being tested is documented at
[dbwarden-org/dbwarden](https://github.com/dbwarden-org/dbwarden).
