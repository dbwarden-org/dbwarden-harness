# MCP Server

The `mcp_server/` package provides an interactive testing server for consumer workflows. It manages workspaces, warm connection pools, and bug report collection.

## Configuration

The MCP server is configured through environment variables:

| Variable | Default | Description |
|---|---|---|
| `DBWARDEN_HARNESS_ROOT` | `/tmp/dbwarden-mcp-workspaces` | Workspace root directory |
| `DBWARDEN_HARNESS_BUG_REPORTS_DIR` | `bug-reports` | Directory for bug report artifacts |
| `MCP_MAX_WORKSPACES` | `20` | Maximum concurrent workspaces |
| `MCP_WARM_POOL_ENABLED` | `1` | Enable warm connection pool |
| `MCP_WARM_POOL_POSTGRES` | `5` | Warm PostgreSQL connections |
| `MCP_WARM_POOL_MYSQL` | `3` | Warm MySQL connections |
| `MCP_WARM_POOL_MARIADB` | `3` | Warm MariaDB connections |
| `MCP_WARM_POOL_CLICKHOUSE` | `3` | Warm ClickHouse connections |
| `MCP_POSTGRES_VERSION` | `16` | PostgreSQL version |
| `MCP_MYSQL_VERSION` | `8.0` | MySQL version |
| `MCP_MARIADB_VERSION` | `11.4` | MariaDB version |
| `MCP_CLICKHOUSE_VERSION` | `24.3` | ClickHouse version |

## Running

```bash
python -m mcp_server
```

The server starts and listens for workspace requests. Each workspace gets its own database and configuration.

## Architecture

| Module | Role |
|---|---|
| `server.py` | Main server entry point |
| `config.py` | Environment-based configuration |
| `workspace.py` | Workspace lifecycle management |
| `pool.py` | Warm connection pool for fast startup |
| `bundle.py` | Workspace packaging and export |
| `classifier.py` | Request classification |
| `comparator.py` | Schema comparison |
| `dumper.py` | Database state dumping |
| `inspector.py` | Schema inspection |
| `mutations.py` | Schema mutation operations |
| `network.py` | Network utilities |
| `track_a.py` / `track_b.py` | Test track definitions |
| `models.py` | Data models |

## See also

- [Environment Variables](reference/environment.md)
- [Repository Layout](reference/layout.md)
