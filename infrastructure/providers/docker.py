from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from testcontainers.core.container import DockerContainer

from infrastructure.providers.base import DatabaseProvider


@dataclass
class DockerDatabaseProvider(DatabaseProvider):
    image: str
    container_port: int
    environment: dict[str, str] = field(default_factory=dict)
    _container: DockerContainer | None = field(default=None, init=False, repr=False)

    def start(self) -> str:
        if self._container is not None:
            return self.url()
        container = DockerContainer(self.image).with_exposed_ports(self.container_port)
        for key, value in self.environment.items():
            container = container.with_env(key, value)
        self._container = container.start()
        self.wait_for_connection()
        return self.url()

    def stop(self) -> None:
        if self._container is not None:
            self._container.stop()
            self._container = None

    def reset(self) -> None:
        raise NotImplementedError("Provider reset must be implemented by the backend")

    def version(self) -> str:
        return self.image.rsplit(":", 1)[-1]

    def diagnostics(self) -> dict[str, Any]:
        details: dict[str, Any] = {
            "image": self.image,
            "container_port": self.container_port,
            "version": self.version(),
            "started": self._container is not None,
        }
        if self._container is not None:
            details["container_id"] = self._container.get_wrapped_container().id
            details["host_port"] = self.host_port()[1]
        return details

    def logs(self) -> str:
        if self._container is None:
            return ""
        logs = self._container.get_logs()
        if isinstance(logs, tuple):
            logs = logs[0]
        if isinstance(logs, bytes):
            return logs.decode("utf-8", errors="replace")
        return str(logs)

    def host_port(self) -> tuple[str, int]:
        if self._container is None:
            raise RuntimeError("Provider is not started")
        return self._container.get_container_host_ip(), int(
            self._container.get_exposed_port(self.container_port)
        )

    def url(self) -> str:
        raise NotImplementedError("Provider URL construction is backend-specific")

    def wait_for_connection(self, timeout: float = 60.0) -> None:
        """Wait for the database engine, not only its published port."""
        from sqlalchemy import create_engine
        from sqlalchemy.exc import SQLAlchemyError

        deadline = time.monotonic() + timeout
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            engine = create_engine(self.url(), pool_pre_ping=True)
            try:
                with engine.connect():
                    return
            except SQLAlchemyError as error:
                last_error = error
                time.sleep(0.5)
            finally:
                engine.dispose()
        raise TimeoutError(f"Database did not become ready: {self.image}") from last_error
