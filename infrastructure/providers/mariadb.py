from __future__ import annotations

from testcontainers.core.network import Network

from infrastructure.providers.mysql import MySQLProvider


class MariaDBProvider(MySQLProvider):
    def __init__(
        self,
        image: str = "mariadb:11.4",
        *,
        database: str = "harness",
        network: Network | None = None,
    ) -> None:
        super().__init__(image=image, database=database, network=network)
