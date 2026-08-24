from __future__ import annotations

from sqlalchemy import create_engine, text

from mcp_server.dumper import dump_database_schema
from mcp_server.workspace import Workspace


def read_workspace_file(workspace: Workspace, relative_path: str) -> str:
    path = workspace.work_dir / relative_path
    return path.read_text(encoding="utf-8")


def inspect_both_schemas(workspace: Workspace) -> tuple[str, str]:
    return (
        dump_database_schema(workspace.track_a_url, workspace.backend),
        dump_database_schema(workspace.track_b_url, workspace.backend),
    )


def query_track_a(workspace: Workspace, sql: str) -> list[dict[str, object]]:
    engine = create_engine(workspace.track_a_url)
    try:
        with engine.connect() as connection:
            result = connection.execute(text(sql))
            return [dict(row._mapping) for row in result.mappings()]
    finally:
        engine.dispose()
