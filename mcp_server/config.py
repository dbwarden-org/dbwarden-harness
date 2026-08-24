from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HarnessMcpConfig:
    """Runtime configuration for the MCP server."""

    max_workspaces: int
    bug_reports_dir: Path
    workspace_root: Path
    warm_pool_enabled: bool
    warm_pool_count: dict[str, int]
    db_versions: dict[str, str]

    @classmethod
    def from_env(cls) -> HarnessMcpConfig:
        root = Path(os.environ.get("DBWARDEN_HARNESS_ROOT", "/tmp/dbwarden-mcp-workspaces"))
        return cls(
            max_workspaces=int(os.environ.get("MCP_MAX_WORKSPACES", "20")),
            bug_reports_dir=Path(
                os.environ.get("DBWARDEN_HARNESS_BUG_REPORTS_DIR", "bug-reports")
            ).resolve(),
            workspace_root=root,
            warm_pool_enabled=os.environ.get("MCP_WARM_POOL_ENABLED", "1") == "1",
            warm_pool_count={
                "postgresql": int(os.environ.get("MCP_WARM_POOL_POSTGRES", "5")),
                "mysql": int(os.environ.get("MCP_WARM_POOL_MYSQL", "3")),
                "mariadb": int(os.environ.get("MCP_WARM_POOL_MARIADB", "3")),
                "clickhouse": int(os.environ.get("MCP_WARM_POOL_CLICKHOUSE", "3")),
                "sqlite": 0,
            },
            db_versions={
                "postgresql": os.environ.get("MCP_POSTGRES_VERSION", "16"),
                "mysql": os.environ.get("MCP_MYSQL_VERSION", "8.0"),
                "mariadb": os.environ.get("MCP_MARIADB_VERSION", "11.4"),
                "clickhouse": os.environ.get("MCP_CLICKHOUSE_VERSION", "24.3"),
                "sqlite": "local",
            },
        )


CONFIG = HarnessMcpConfig.from_env()
