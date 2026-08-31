# Compatibility Findings

The harness is strict about observed behaviour and explicit about release
limitations. Findings are listed per release in
[Known Findings by Release](../known-compatibility.md); this page covers how to
read and operate them.

## Current release under test

`pyproject.toml` declares the dbwarden version the harness resolves by default.
The findings recorded against it are summarized in the coverage matrix and
detailed in the per-release page.

Findings observed on `0.17.1` cluster in two places: SQLite table constraints
are rendered with PostgreSQL syntax that SQLite cannot parse, and generated
integer primary keys are missing on MySQL and MariaDB. Both are invisible to a
test that stops at a zero exit code, which is why the semantics suite writes
rows.

## Reading experimental results

An experimental failure is still a test result. It is allowed to avoid making
the overall scheduled workflow red while the package defect is known. It must
remain visible in logs, artifacts, and the per-release page. When a new dbwarden
release is available, rerun the cell. A strict unexpected pass also requires
review so the compatibility policy can be updated deliberately.

## Promoting a finding

A finding is removed when a published release passes the test that produced it,
not when a checkout does. The intermediate state - fixed in the core checkout,
not yet released - is recorded in the finding itself, so a reader can tell
"already fixed, waiting for a release" from "unresolved".

To check a candidate before it ships, install the wheel into the harness
environment and rerun the suite; see
[Running Tests](../getting-started/running-tests.md#certify-a-candidate-wheel).

## Reproduction

```bash
uv run pytest -q suites/semantics -m "not integration"
DBWARDEN_HARNESS_RUN_INTEGRATION=1 uv run pytest -m integration suites/semantics
DBWARDEN_HARNESS_RUN_INTEGRATION=1 uv run pytest -m integration suites/round_trip -k mariadb
DBWARDEN_HARNESS_RUN_INTEGRATION=1 uv run pytest -m integration suites/round_trip -k mysql
```
