# Compatibility Findings

The harness is strict about observed behaviour and explicit about release
limitations. Findings are listed per release in
[Known Findings by Release](../known-compatibility.md); this page covers how to
read and operate them.

## Current release under test

`pyproject.toml` declares the dbwarden version the harness resolves by default,
and `[tool.uv.sources]` points it at the sibling `../dbwarden` checkout so the
latest source is exercised. The findings recorded against it are summarized in
the coverage matrix and detailed in the per-release page.

The `0.17.1` findings are fixed on the `0.19.0` source: SQLite table
constraints are emitted inside `CREATE TABLE`, integer primary keys carry
`AUTO_INCREMENT` on MySQL and MariaDB, and configuration-declared objects are
diffed against the live snapshot. The semantics and plugin suites confirm each
one by writing rows and re-reading the catalog.

## Reading experimental results

An experimental failure is still a test result. It is allowed to avoid making
the overall scheduled workflow red while the package defect is known. It must
remain visible in logs, artifacts, and the per-release page. When a new dbwarden
release is available, rerun the cell. A strict unexpected pass also requires
review so the compatibility policy can be updated deliberately.

## Promoting a finding

A finding is removed when the source under test passes the test that produced
it. Because the harness resolves the sibling checkout, a fix is credited as soon
as it lands; the historical entry stays on the per-release page so a reader can
still see what an earlier publication did.

To check a published candidate instead, install the wheel with
`uv sync --no-sources` and rerun the suite; see
[Running Tests](../getting-started/running-tests.md#certify-a-candidate-wheel).

## Reproduction

```bash
uv run pytest -q suites/semantics -m "not integration"
DBWARDEN_HARNESS_RUN_INTEGRATION=1 uv run pytest -m integration suites/semantics
DBWARDEN_HARNESS_RUN_INTEGRATION=1 uv run pytest -m integration suites/round_trip -k mariadb
DBWARDEN_HARNESS_RUN_INTEGRATION=1 uv run pytest -m integration suites/round_trip -k mysql
```
