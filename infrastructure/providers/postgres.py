from __future__ import annotations

from infrastructure.providers.docker import DockerDatabaseProvider


class PostgresProvider(DockerDatabaseProvider):
    def __init__(self, image: str = "postgres:17", *, database: str = "harness") -> None:
        super().__init__(
            image=image,
            container_port=5432,
            environment={"POSTGRES_USER": "harness", "POSTGRES_PASSWORD": "harness", "POSTGRES_DB": database},
        )
        self.database = database

    def url(self) -> str:
        host, port = self.host_port()
        return f"postgresql+psycopg2://harness:harness@{host}:{port}/{self.database}"

    def reset(self) -> None:
        from sqlalchemy import create_engine, text

        engine = create_engine(self.url())
        try:
            with engine.begin() as connection:
                connection.execute(text("DROP SCHEMA public CASCADE"))
                connection.execute(text("CREATE SCHEMA public"))
        finally:
            engine.dispose()
