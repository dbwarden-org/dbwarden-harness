from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Self

from testcontainers.core.network import Network

logger = logging.getLogger(__name__)


@dataclass
class WorkspaceNetwork:
    """A Docker bridge network scoped to one workspace."""

    network: Network
    network_id: str
    name: str

    @classmethod
    def create(cls) -> WorkspaceNetwork:
        network = Network(docker_network_kw={"driver": "bridge", "internal": False})
        network.create()
        network_id = network.id
        if network_id is None:
            raise RuntimeError("Docker network creation did not return an id")
        return cls(network=network, network_id=network_id, name=network.name)

    def connect(self, container_id: str) -> None:
        self.network.connect(container_id)

    def disconnect(self, container_id: str) -> None:
        try:
            self.network._unwrap_network.disconnect(container_id)
        except Exception:  # noqa: BLE001 - container may already be gone
            logger.debug("Network disconnect failed for %s", container_id)

    def remove(self) -> None:
        try:
            self.network.remove()
        except Exception:  # noqa: BLE001 - network may already be gone
            logger.debug("Network remove failed for %s", self.network_id)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.remove()
