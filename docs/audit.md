# Documentation and API audit

Audit date: 2026-09-23. Local Windows checkout, using the current editable sibling dbwarden checkout. No changes were published.

## Scope

Reviewed repository Markdown, site navigation, configuration, CI, provider and helper APIs, nine MCP tools, reference schemas, CLI workflows and skip conditions. Added a generated [Python API inventory](reference/python-api.md) and a repeatable documentation checker. It verifies inventory drift, navigation, file links, Python snippet syntax, environment-variable coverage and MCP-tool coverage.

The checker does not execute every snippet or establish live behavior for every backend. The generated API page inventories public definitions and fields, including abstract provider contracts.

## Corrected behavior

| Finding | Change and evidence |
| --- | --- |
| Convergence parser returned an empty list for missing or malformed JSON | Requests JSON explicitly and rejects invalid output. A staged rollback test had no configured models; it now declares the expected columns and index and checks real drift. |
| Safety tests assumed destructive migration approval was unnecessary | Destructive constraint tests pass `--force` and still verify preserved data and remaining constraints. Offline error assertions match the current nonzero contract. |
| SQL baseline omitted current safety headers | Updated the SQLite baseline and its SHA-256 manifest; table DDL is unchanged. |
| Missing scope and merge coverage | Added real CLI projects for offline split generation, trusted plan chains, capped application, resume, malformed plans, state aliases and real Git branch collisions. |
| MCP read/write paths escaped workspaces | Shared resolved-path validation rejects absolute paths, drive paths and escapes. Frozen workspaces reject changes. |
| Read-only queries were not enforced and row conversion failed | Query validation plus backend read-only settings; real SQLite tests verify rejected writes, returned rows and explicit-write commits. |
| SQLite MCP dumps required an external executable | Uses standard-library SQLite with read-only connections. Both reference modes now run in ordinary local tests. |
| Comparator modified literals and lost table options | SQL parsing preserves literals, qualified identifiers, constraint names and options. Regression cases cover defaults, checks, engines, autoincrement and SQLite INTEGER versus INT primary keys. Unsupported syntax raises. |
| Mutation helpers lost index columns or uniqueness | AST edits preserve requested index fields and add missing imports. Tests load resulting SQLAlchemy metadata for every mutation kind. Defaults edit client-side `default`, not `server_default`. |
| Incremental reference used hand-written type mapping and stale bytecode | Compiles added columns from mutated metadata; loads supplied source directly. Same-size source changes have a regression test. |
| ClickHouse HTTP provider URLs were passed to generic SQLAlchemy | Converts them to the installed dialect, preserving credentials and HTTPS settings. URL conversion has local coverage; server execution is unverified. |
| Pool could return the wrong server version | Claims match requested versions; failed connection/reset discards the provider. |
| Plan reader and classifier expected obsolete layouts | Reads adjacent plans and current operation/type fields; nested exotic types remain outside the standard category. |
| Dump subprocess environment and encoded credentials were mishandled | Preserves the parent environment, decodes URL fields and passes passwords outside command arguments. Command construction is tested with mocks. |
| JUnit wrapper totals reported zero | Aggregates contained suite totals; tests cover wrapped and bare suite reports. |

## Documentation corrections

Removed repeated promotional prose and corrected install instructions, SQLite coverage, slow-test selection, artifact ownership, plugin loading, provider status and private-import checks. MCP documentation now covers all tools, mutations, reference-mode fallback, classification labels and trust boundaries. Exported state JSON has no embedded integrity checksum; the harness's file manifest is a separate check.

## Validation

Run evidence is retained in local `.audit-*.log` files, excluded from Git.

| Check | Result |
| --- | --- |
| Full suite, two workers with benchmark timing disabled | 151 passed, 289 skipped in 139.04 seconds; `.data-harness-final-tests.log` |
| Parallel offline/scope/Git-merge cases | 3 passed; `.audit-merge-parallel.log` |
| API boundary and semantic regressions | 40 passed; `.audit-edge-final.log` |
| Serial snapshot benchmark test | 1 passed; `.audit-benchmark-final.log` |
| Runtime MCP registration | All nine tools exposed; queries default to read-only |
| Documentation audit | 69 Markdown documents, 112 Python snippets, 53 source modules, nine MCP tools, 22 environment variables; no issues |
| Ruff, strict Zensical build, diff whitespace | Passed |

An initial parallel run passed 141 cases and failed once while importing Python's `_overlapped` module, before merge code loaded: Windows error 10106, service provider initialization failure. The child environment retained `SYSTEMROOT`, `WINDIR` and `PATH`; the host had ample free memory. Forty parallel Python/dbwarden startup checks, the parallel merge/scope tests and the final full parallel suite passed afterward. No retry, skip or serialization workaround was added. These checks did not establish the operating-system failure's cause.

The harness's Docker-gated PostgreSQL, MySQL, MariaDB and ClickHouse suites were skipped because the Docker engine pipe was unavailable. WSL2 also could not start because host virtualization was disabled, so ClickHouse could not be qualified locally. Separate core evidence exercised native PostgreSQL, MariaDB and MySQL data paths; it does not make the skipped harness Docker suites pass. SQLite and mocked boundary tests do not establish server correctness. Model source executes as trusted Python; the MCP server does not sandbox it. Read-only bundle files are not immutable storage. Process-crash, power-loss and arbitrary external plugin behavior are outside this run's evidence.

## Reproduce

```bash
uv sync --group dev --reinstall-package dbwarden
uv run pytest -q
uv run ruff check .
uv run python -m tools.check_docs
uv run zensical build --strict
```

Parallel correctness runs can use `uv run pytest -n 2 --benchmark-disable -q`. This executes benchmark fixtures once without timing them; run benchmark measurements separately without workers.
