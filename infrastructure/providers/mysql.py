from __future__ import annotations

from testcontainers.core.network import Network

from infrastructure.providers.docker import DockerDatabaseProvider


class MySQLProvider(DockerDatabaseProvider):
    def __init__(
        self,
        image: str = "mysql:8.4",
        *,
        database: str = "harness",
        network: Network | None = None,
    ) -> None:
        super().__init__(
            image=image,
            container_port=3306,
            environment={"MYSQL_ROOT_PASSWORD": "harness", "MYSQL_DATABASE": database, "MYSQL_USER": "harness", "MYSQL_PASSWORD": "harness"},
            network=network,
        )
        self.database = database

    def url(self) -> str:
        host, port = self.host_port()
        return f"mysql+pymysql://harness:harness@{host}:{port}/{self.database}"

    def reset(self) -> None:
        from sqlalchemy import create_engine, text

        engine = create_engine(self.url())
        try:
            with engine.begin() as connection:
                tables = connection.execute(text("SHOW TABLES")).scalars().all()
                connection.execute(text("SET FOREIGN_KEY_CHECKS=0"))
                for table in tables:
                    connection.execute(text(f"DROP TABLE `{table}`"))
                connection.execute(text("SET FOREIGN_KEY_CHECKS=1"))
        finally:
            engine.dispose()
