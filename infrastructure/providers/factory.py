from __future__ import annotations

from infrastructure.providers.base import DatabaseProvider
from infrastructure.providers.clickhouse import ClickHouseProvider
from infrastructure.providers.mariadb import MariaDBProvider
from infrastructure.providers.mysql import MySQLProvider
from infrastructure.providers.postgres import PostgresProvider


def provider_for(backend: str, version: str) -> DatabaseProvider:
    """Build a matrix provider without starting a container."""
    constructors = {
        "postgres": lambda: PostgresProvider(image=f"postgres:{version}"),
        "postgresql": lambda: PostgresProvider(image=f"postgres:{version}"),
        "mysql": lambda: MySQLProvider(image=f"mysql:{version}"),
        "mariadb": lambda: MariaDBProvider(image=f"mariadb:{version}"),
        "clickhouse": lambda: ClickHouseProvider(
            image=f"clickhouse/clickhouse-server:{version}"
        ),
    }
    try:
        return constructors[backend.lower()]()
    except KeyError as error:
        supported = ", ".join(sorted(constructors))
        raise ValueError(f"Unsupported backend {backend!r}; choose one of {supported}") from error
