from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url

from mcp_server.dumper import dump_database_schema
from mcp_server.workspace import Workspace


def read_workspace_file(workspace: Workspace, relative_path: str) -> str:
    path = workspace.resolve_path(relative_path)
    return path.read_text(encoding="utf-8")


def inspect_both_schemas(workspace: Workspace) -> tuple[str, str]:
    return (
        dump_database_schema(workspace.track_a_url, workspace.backend),
        dump_database_schema(workspace.track_b_url, workspace.backend),
    )


def sqlalchemy_url(database_url: str) -> URL:
    """Translate ClickHouse HTTP provider URLs to the installed SQLAlchemy driver."""
    url = make_url(database_url)
    if url.drivername in {"http", "https"}:
        secure = url.drivername == "https"
        url = url.set(drivername="clickhousedb", port=url.port or (8443 if secure else 8123))
        if secure:
            url = url.update_query_dict({"secure": "true"})
    return url


def query_track_a(
    workspace: Workspace, sql: str, read_only: bool = True
) -> list[dict[str, object]]:
    """Query Track A, guarding reads and committing explicitly enabled writes."""
    if workspace.frozen and not read_only:
        raise RuntimeError("Cannot write to a frozen workspace")
    if read_only:
        from sqlglot import exp, parse

        dialect = {"postgresql": "postgres", "mariadb": "mysql"}.get(
            workspace.backend, workspace.backend
        )
        statements = parse(sql, read=dialect)
        if (
            len(statements) != 1
            or not isinstance(statements[0], exp.Query)
            or any(
                isinstance(node, (exp.DDL, exp.DML, exp.Into, exp.Lock))
                for node in statements[0].walk()
            )
        ):
            raise ValueError("read_only requires one SELECT query without writes or locks")
    engine = create_engine(sqlalchemy_url(workspace.track_a_url))
    try:
        with engine.begin() as connection:
            if read_only:
                guard = {
                    "sqlite": "PRAGMA query_only = ON",
                    "postgresql": "SET TRANSACTION READ ONLY",
                    "mysql": "START TRANSACTION READ ONLY",
                    "mariadb": "START TRANSACTION READ ONLY",
                    "clickhouse": "SET readonly = 1",
                }.get(workspace.backend)
                if guard is None:
                    raise ValueError(f"Read-only queries unsupported for {workspace.backend}")
                connection.execute(text(guard))
            result = connection.execute(text(sql))
            return [dict(row) for row in result.mappings()] if result.returns_rows else []
    finally:
        engine.dispose()
