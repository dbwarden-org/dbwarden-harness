# MCP Server

The server exposes nine tools for disposable two-database experiments. Track A runs the installed dbwarden CLI; Track B builds a SQLAlchemy reference schema. Their schema dumps are compared, and failing workspaces can be frozen with proof bundles.

## Start

```bash
uv run python -m mcp_server
```

Transport is MCP over standard input/output, with no HTTP listener. Configure this command in an MCP client. Model files contain executable Python and must come from trusted callers.

SQLite needs no Docker. For SQLite-only use:

```powershell
$env:MCP_WARM_POOL_ENABLED = '0'
uv run python -m mcp_server
```

Importing `mcp_server.server` registers tools without starting containers. `run_server()` starts the warm pool and shuts it down on exit.

## Tools

Tools return JSON encoded as text. Invalid input raises a tool error.

| Tool | Arguments | Behavior |
| --- | --- | --- |
| `initialize_workspace` | `backend`, optional `db_version`, `name_prefix` | Creates Track A/B providers; returns ID, backend/version, directory and URLs. Backends: sqlite, postgresql (postgres alias), mysql, mariadb, clickhouse. Prefix accepts 1–64 letters, digits, underscores or hyphens. |
| `destroy_workspace` | `workspace_id` | Releases providers and active registration. Unknown ID returns `removed: false`. Files remain on disk. |
| `list_workspaces` | None | Returns IDs, backend/version, paths, creation times and frozen status. |
| `write_model_file` | `workspace_id`, `relative_path`, `content` | Writes within workspace and returns byte count. `app/models.py` updates initial/current source. Rejects absolute paths, resolved escapes and frozen-workspace writes. |
| `apply_mutation` | `workspace_id`, `mutation` | Edits current model source and records mutation; returns source and applied mutations. Frozen workspaces reject changes. |
| `run_two_track_test` | `workspace_id`, `reference_mode="nuclear"` | Returns track stages, errors, plan, schema differences, classification and optional bundle path. Mode must be nuclear or incremental. |
| `read_file` | `workspace_id`, `relative_path` | Reads UTF-8 text inside workspace, including frozen workspaces. |
| `inspect_schema` | `workspace_id` | Returns native dumps for both databases. Individual failures appear as `ERROR: ...` strings. |
| `query_database` | `workspace_id`, `sql`, `read_only=true` | Queries Track A and returns row objects. Writes require false and commit on success. Statements without rows return an empty list. Frozen workspaces allow only reads. |

Read-only SQL must parse as one query without DDL, DML, `INTO`, or row locks. Connections also enable backend read-only mode. This protects database state; it does not sandbox model Python or guarantee database functions have no external effects. SQLite guards have local coverage; server guards require backend integration runs.

## Mutations

Helpers edit annotated `Mapped[...] = mapped_column(...)` declarations through Python's AST. Rendering changes formatting and removes comments. Type changes require the first positional argument to be a SQLAlchemy type. Missing type imports are added. Unsupported source shapes raise `MutationError`; use `write_model_file` to preserve formatting or supply arbitrary code.

| `type` | Required fields | Optional fields |
| --- | --- | --- |
| `add_column` | table, column, column_type | nullable (true), default |
| `change_type` | table, column, new_type | None |
| `add_index` | table, columns | unique (false); adds a SQLAlchemy Index with all listed columns, preserving literal table options |
| `drop_column` | table, column | None |
| `set_not_null`, `drop_not_null` | table, column | None |
| `set_default` | table, column, default | None |
| `drop_default` | table, column | None |

## Reference modes and limits

`set_default` and `drop_default` edit the SQLAlchemy client-side `default` argument. They do not edit `server_default`. Dropping a column does not rewrite constraints or indexes that reference it.

`nuclear` recreates reference schema from current SQLAlchemy metadata. `incremental` compiles recorded add-column mutations from mutated metadata with the backend dialect; other mutations and an empty list fall back to recreation. These paths compare structure, not data preservation or dbwarden metadata that SQLAlchemy does not emit.

SQLite dumps use Python's standard library. PostgreSQL requires `pg_dump` on PATH; MySQL and MariaDB require `mysqldump`. ClickHouse uses its client. The comparator parses SQL and retains literals, qualified identifiers, constraint names and table options. It ignores dbwarden bookkeeping tables, sorts statements and table constraints, and canonicalizes simple primary keys. Unsupported SQL raises an error. Equivalent but differently named constraints still differ; use matching naming conventions in both models.

Classification values `95` and `5` label standard versus unsupported/exotic paths. They are not measured success rates or confidence scores. Bundles retain models, migration artifacts, dumps, differences and reproduction material. Bundle files are read-only with a hash manifest, not immutable storage. Frozen workspaces remain readable.

Track A reads plans beside SQL in `migrations/primary/`. Errors retain stdout and stderr. Pool claims match requested provider version.

## Configuration

| Variable | Default | Effect |
| --- | --- | --- |
| `DBWARDEN_HARNESS_ROOT` | `/tmp/dbwarden-mcp-workspaces` | Workspace directory; override on Windows if needed. |
| `DBWARDEN_HARNESS_BUG_REPORTS_DIR` | bug-reports | Proof bundle directory. |
| `MCP_MAX_WORKSPACES` | 20 | Active workspace limit. |
| `MCP_WARM_POOL_ENABLED` | 1 | Starts pool when equal to 1. |
| `MCP_WARM_POOL_POSTGRES` | 5 | PostgreSQL container target. |
| `MCP_WARM_POOL_MYSQL` | 3 | MySQL container target. |
| `MCP_WARM_POOL_MARIADB` | 3 | MariaDB container target. |
| `MCP_WARM_POOL_CLICKHOUSE` | 3 | ClickHouse container target. |
| `MCP_POSTGRES_VERSION` | 16 | PostgreSQL image tag. |
| `MCP_MYSQL_VERSION` | 8.0 | MySQL image tag. |
| `MCP_MARIADB_VERSION` | 11.4 | MariaDB image tag. |
| `MCP_CLICKHOUSE_VERSION` | 24.3 | ClickHouse image tag. |

See [Python API](reference/python-api.md) for signatures and fields, and [Environment Variables](reference/environment.md) for suite settings.
