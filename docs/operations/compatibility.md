# Compatibility Findings

The harness is strict about observed behavior and explicit about release
limitations.

## PyPI 0.16.5

- MariaDB migration generation can create a foreign-key child table before its
  referenced parent table.
- MySQL reverse engineering can report an incomplete `varchar` type during a
  full-version final diff.
- Default reverse engineering can include dbwarden bookkeeping tables in the
  generated model file.

The harness excludes dbwarden-owned tables for the supported application model
round trip. The MariaDB generate-models case remains a strict XFAIL, and the
MySQL and MariaDB full-version cells are experimental in CI.

## Reading experimental results

An experimental failure is still a test result. It is allowed to avoid making
the overall scheduled workflow red while the package defect is known. It must
remain visible in logs, artifacts, and this document. When a new dbwarden
release is available, rerun the cell. A strict unexpected pass also requires
review so the compatibility policy can be updated deliberately.

## Reproduction

```bash
DBWARDEN_HARNESS_RUN_INTEGRATION=1 uv run pytest -m integration suites/round_trip -k mariadb
DBWARDEN_HARNESS_RUN_INTEGRATION=1 uv run pytest -m integration suites/round_trip -k mysql
```
