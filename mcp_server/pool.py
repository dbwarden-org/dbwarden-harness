from __future__ import annotations

import logging
import threading
import time
from collections import deque

from infrastructure.providers.base import DatabaseProvider
from infrastructure.providers.factory import provider_for
from mcp_server.config import CONFIG
from mcp_server.network import WorkspaceNetwork

logger = logging.getLogger(__name__)


class ContainerPool:
    """Warm pool of pre-started database containers keyed by backend."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._queues: dict[str, deque[DatabaseProvider]] = {backend: deque() for backend in CONFIG.warm_pool_count}
        self._stopped = False
        self._refill_thread: threading.Thread | None = None

    def start(self) -> None:
        if not CONFIG.warm_pool_enabled:
            return
        self._stopped = False
        self._refill_thread = threading.Thread(target=self._refill_loop, daemon=True)
        self._refill_thread.start()

    def stop(self) -> None:
        self._stopped = True
        with self._lock:
            for queue in self._queues.values():
                while queue:
                    provider = queue.popleft()
                    self._safe_stop(provider)

    def _refill_loop(self) -> None:
        while not self._stopped:
            try:
                self._top_up()
            except Exception:
                logger.exception("Warm pool refill failed")
            time.sleep(2.0)

    def _top_up(self) -> None:
        for backend, target in CONFIG.warm_pool_count.items():
            if backend == "sqlite":
                continue
            with self._lock:
                queue = self._queues[backend]
                current = len(queue)
            version = CONFIG.db_versions.get(backend, "latest")
            for _ in range(target - current):
                try:
                    provider = provider_for(backend, version)
                    provider.start()
                    with self._lock:
                        queue.append(provider)
                except Exception:
                    logger.exception("Failed to warm-start %s", backend)
                    break

    def claim(
        self,
        backend: str,
        version: str,
        workspace_network: WorkspaceNetwork,
    ) -> DatabaseProvider:
        backend = backend.lower()
        if backend == "sqlite":
            raise ValueError("SQLite does not use container pool")

        with self._lock:
            queue = self._queues.get(backend, deque())
            if queue:
                provider = queue.popleft()
            else:
                provider = None

        if provider is None:
            provider = provider_for(backend, version)
            provider.start()

        try:
            provider.reset()
        except Exception:
            self._safe_stop(provider)
            raise

        container = getattr(provider, "_container", None)
        if container is not None:
            container_id = container.get_wrapped_container().id
            workspace_network.connect(container_id)

        return provider

    def release(
        self,
        backend: str,
        provider: DatabaseProvider,
        workspace_network: WorkspaceNetwork | None,
    ) -> None:
        if backend == "sqlite":
            self._safe_stop(provider)
            return

        if workspace_network is not None:
            container = getattr(provider, "_container", None)
            if container is not None:
                container_id = container.get_wrapped_container().id
                workspace_network.disconnect(container_id)

        if self._stopped:
            self._safe_stop(provider)
            return

        try:
            provider.reset()
        except Exception:  # noqa: BLE001 - failed reset means discard
            self._safe_stop(provider)
            return

        with self._lock:
            self._queues.setdefault(backend, deque()).append(provider)

    def _safe_stop(self, provider: DatabaseProvider) -> None:
        try:
            provider.stop()
        except Exception:
            logger.exception("Failed to stop provider")


POOL = ContainerPool()
