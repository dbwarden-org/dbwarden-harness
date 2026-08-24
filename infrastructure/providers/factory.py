from __future__ import annotations

from testcontainers.core.network import Network

from infrastructure.providers.base import DatabaseProvider
from infrastructure.providers.clickhouse import ClickHouseProvider
from infrastructure.providers.mariadb import MariaDBProvider
from infrastructure.providers.mysql import MySQLProvider
from infrastructure.providers.postgres import PostgresProvider


def provider_for(
    backend: str,
    version: str,
    *,
    network: Network | None = None,
) -> DatabaseProvider:
    """Build a matrix provider without starting a container."""
    constructors = {
        "postgres": lambda: PostgresProvider(image=f"postgres:{version}", network=network),
        "postgresql": lambda: PostgresProvider(image=f"postgres:{version}", network=network),
        "mysql": lambda: MySQLProvider(image=f"mysql:{version}", network=network),
        "mariadb": lambda: MariaDBProvider(image=f"mariadb:{version}", network=network),
        "clickhouse": lambda: ClickHouseProvider(
            image=f"clickhouse/clickhouse-server:{version}",
            network=network,
        ),
    }
    try:
        return constructors[backend.lower()]()
    except KeyError as error:
        supported = ", ".join(sorted(constructors))
        raise ValueError(f"Unsupported backend {backend!r}; choose one of {supported}") from error
