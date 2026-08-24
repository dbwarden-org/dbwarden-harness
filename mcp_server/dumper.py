from __future__ import annotations

import shutil
import subprocess
import urllib.parse
from pathlib import Path


class SchemaDumpError(RuntimeError):
    """Raised when a native schema dump fails."""


def dump_database_schema(database_url: str, backend: str) -> str:
    """Dump the schema of a live database using backend-native tooling."""
    backend = backend.lower()
    if backend == "postgresql":
        return _dump_postgresql(database_url)
    if backend in {"mysql", "mariadb"}:
        return _dump_mysql(database_url)
    if backend == "sqlite":
        return _dump_sqlite(database_url)
    if backend == "clickhouse":
        return _dump_clickhouse(database_url)
    raise SchemaDumpError(f"Unsupported backend for schema dump: {backend}")


def _dump_postgresql(database_url: str) -> str:
    pg_dump = shutil.which("pg_dump")
    if pg_dump is None:
        raise SchemaDumpError("pg_dump not found on PATH")

    url = _normalize_for_cli(database_url, default_scheme="postgresql")
    parsed = urllib.parse.urlparse(url)
    args = [
        pg_dump,
        "--schema-only",
        "--no-owner",
        "--no-privileges",
        "--no-comments",
    ]
    env = {}
    if parsed.hostname:
        args.extend(["-h", parsed.hostname])
    if parsed.port:
        args.extend(["-p", str(parsed.port)])
    if parsed.username:
        args.extend(["-U", parsed.username])
    if parsed.password:
        env["PGPASSWORD"] = parsed.password
    args.append(parsed.path.lstrip("/") or "harness")

    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
        check=False,
    )
    if result.returncode != 0:
        raise SchemaDumpError(f"pg_dump failed: {result.stderr}")
    return result.stdout


def _dump_mysql(database_url: str) -> str:
    mysqldump = shutil.which("mysqldump")
    if mysqldump is None:
        raise SchemaDumpError("mysqldump not found on PATH")

    url = _normalize_for_cli(database_url, default_scheme="mysql")
    parsed = urllib.parse.urlparse(url)
    args = [mysqldump, "--no-data", "--skip-comments"]
    if parsed.hostname:
        args.extend(["-h", parsed.hostname])
    if parsed.port:
        args.extend(["-P", str(parsed.port)])
    if parsed.username:
        args.extend(["-u", parsed.username])
    if parsed.password:
        args.extend([f"-p{parsed.password}"])
    args.append(parsed.path.lstrip("/") or "harness")

    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if result.returncode != 0:
        raise SchemaDumpError(f"mysqldump failed: {result.stderr}")
    return result.stdout


def _dump_sqlite(database_url: str) -> str:
    parsed = urllib.parse.urlparse(database_url)
    path = Path(parsed.path)
    sqlite3 = shutil.which("sqlite3")
    if sqlite3 is None:
        raise SchemaDumpError("sqlite3 CLI not found on PATH")
    if not path.exists():
        return ""
    result = subprocess.run(
        [sqlite3, str(path), ".schema"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        raise SchemaDumpError(f"sqlite3 .schema failed: {result.stderr}")
    return result.stdout


def _dump_clickhouse(database_url: str) -> str:
    import clickhouse_connect

    parsed = urllib.parse.urlparse(database_url)
    query = urllib.parse.parse_qs(parsed.query)
    client = clickhouse_connect.get_client(
        host=parsed.hostname or "localhost",
        port=parsed.port or 8123,
        username=parsed.username or "clickhouse",
        password=parsed.password or "clickhouse",
        database=parsed.path.lstrip("/") or "harness",
        secure=parsed.scheme == "https",
        **{key: values[-1] for key, values in query.items()},
    )
    try:
        database = parsed.path.lstrip("/") or "harness"
        rows = client.query(
            "SELECT name FROM system.tables WHERE database = %(database)s AND is_temporary = 0 ORDER BY name",
            parameters={"database": database},
        ).result_rows
        statements: list[str] = []
        for (table,) in rows:
            create = client.query(f"SHOW CREATE TABLE {database}.`{table}`").result_rows
            if create:
                statements.append(create[0][0])
        return "\n\n".join(statements) + "\n"
    finally:
        client.close()


def _normalize_for_cli(database_url: str, default_scheme: str) -> str:
    """Convert SQLAlchemy URLs (e.g. postgresql+psycopg2://) to driverless form."""
    parsed = urllib.parse.urlparse(database_url)
    scheme = default_scheme
    return urllib.parse.urlunparse(
        (scheme, parsed.netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)
    )
