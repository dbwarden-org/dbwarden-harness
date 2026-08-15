from __future__ import annotations

from infrastructure.providers.mysql import MySQLProvider


class MariaDBProvider(MySQLProvider):
    def __init__(self, image: str = "mariadb:11.4", *, database: str = "harness") -> None:
        super().__init__(image=image, database=database)
