from __future__ import annotations

import time

from infrastructure.providers.docker import DockerDatabaseProvider


class ClickHouseProvider(DockerDatabaseProvider):
    def __init__(self, image: str = "clickhouse/clickhouse-server:24.3", *, database: str = "harness") -> None:
        super().__init__(
            image=image,
            container_port=8123,
            environment={
                "CLICKHOUSE_DB": database,
                "CLICKHOUSE_USER": "clickhouse",
                "CLICKHOUSE_PASSWORD": "clickhouse",
                "CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT": "1",
            },
        )
        self.database = database

    def url(self) -> str:
        host, port = self.host_port()
        return f"http://clickhouse:clickhouse@{host}:{port}/{self.database}"

    def reset(self) -> None:
        client = self._client()
        for (table,) in client.query("SHOW TABLES").result_rows:
            client.command(f"DROP TABLE IF EXISTS `{table}`")
        client.close()

    def wait_for_connection(self, timeout: float = 60.0) -> None:
        deadline = time.monotonic() + timeout
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            try:
                client = self._client()
                client.command("SELECT 1")
                client.close()
                return
            except Exception as error:  # noqa: BLE001 - driver errors vary by release
                last_error = error
                time.sleep(0.5)
        raise TimeoutError(f"Database did not become ready: {self.image}") from last_error

    def _client(self):
        import clickhouse_connect

        host, port = self.host_port()
        return clickhouse_connect.get_client(
            host=host,
            port=port,
            username="clickhouse",
            password="clickhouse",
            database=self.database,
        )
