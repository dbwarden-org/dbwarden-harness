# Environment Variables

| Variable | Effect |
| --- | --- |
| `DBWARDEN_HARNESS_RUN_INTEGRATION` | Enables Docker and provider tests when set to `1`. |
| `DBWARDEN_HARNESS_RUN_SCALE` | Enables scale benchmarks when set to `1`. |
| `DBWARDEN_HARNESS_RUN_500_MIGRATION` | Enables the expensive 500 migration benchmark when set to `1`. |
| `DBWARDEN_HARNESS_DEFER_EXECUTABLE` | Points benchmark comparison at a dbwarden checkout executable. |
| `DBWARDEN_HARNESS_DEFER_SNAPSHOTS` | Enables deferred snapshot mode in benchmark helpers. |
| `DBWARDEN_HARNESS_BACKEND` | Limits provider matrix lifecycle cases to one backend. |
| `DBWARDEN_HARNESS_VERSIONS` | Limits provider matrix lifecycle cases to listed versions. |
| `DBWARDEN_HARNESS_ARTIFACT_DIR` | Writes failed test artifacts to the selected directory. |
| `DBWARDEN_HARNESS_CLICKHOUSE_URL` | ClickHouse connection URL for generative suite. |
| `DBWARDEN_HARNESS_CLICKHOUSE_VERSION` | ClickHouse image version for generative suite (default `26.6`). |
| `DBWARDEN_HARNESS_ENFORCE_PERFORMANCE` | When set to `1`, the 500-migration benchmark asserts against a performance baseline instead of measuring only. |
| `DBWARDEN_HARNESS_ROOT` | Workspace root directory for the MCP server (default `/tmp/dbwarden-mcp-workspaces`). |
| `DBWARDEN_HARNESS_BUG_REPORTS_DIR` | Directory for MCP server bug report artifacts (default `bug-reports`). |
| `MCP_MAX_WORKSPACES` | Maximum concurrent MCP workspaces (default `20`). |
| `MCP_WARM_POOL_ENABLED` | Enable MCP warm connection pool (default `1`). |
| `MCP_WARM_POOL_POSTGRES` | Number of warm PostgreSQL connections in MCP pool (default `5`). |
| `MCP_WARM_POOL_MYSQL` | Number of warm MySQL connections in MCP pool (default `3`). |
| `MCP_WARM_POOL_MARIADB` | Number of warm MariaDB connections in MCP pool (default `3`). |
| `MCP_WARM_POOL_CLICKHOUSE` | Number of warm ClickHouse connections in MCP pool (default `3`). |
| `MCP_POSTGRES_VERSION` | PostgreSQL version for MCP server (default `16`). |
| `MCP_MYSQL_VERSION` | MySQL version for MCP server (default `8.0`). |
| `MCP_MARIADB_VERSION` | MariaDB version for MCP server (default `11.4`). |
| `MCP_CLICKHOUSE_VERSION` | ClickHouse version for MCP server (default `24.3`). |

Variables beginning with `DBWARDEN_HARNESS_` are included in command artifact
metadata so a run can be reproduced.
