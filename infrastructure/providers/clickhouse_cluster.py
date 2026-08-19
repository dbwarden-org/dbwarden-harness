from __future__ import annotations

import contextlib
import socket
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any

from testcontainers.core.container import DockerContainer
from testcontainers.core.network import Network

from infrastructure.providers.base import DatabaseProvider


class ClickHouseClusterProvider(DatabaseProvider):
    """A two-node ClickHouse cluster with a shared ClickHouse Keeper.

    The cluster is configured as a single shard with two replicas:

    * ``ch-keeper`` – ClickHouse Keeper on the internal Docker network.
    * ``ch-node1`` / ``ch-node2`` – clickhouse-server replicas, reachable over
      the internal network by alias, with HTTP ports mapped to the host.

    The mounted ``cluster.xml`` defines the ``harness_cluster`` remote server
    group, ``{shard}`` / ``{replica}`` macros, and a ``<zookeeper>`` entry
    pointing at Keeper so ``ReplicatedMergeTree`` engines can coordinate.
    """

    def __init__(
        self,
        image: str = "clickhouse/clickhouse-server:24.3",
        keeper_image: str = "clickhouse/clickhouse-keeper:24.3",
        *,
        database: str = "harness",
    ) -> None:
        self.image = image
        self.keeper_image = keeper_image
        self.database = database
        self._user = "clickhouse"
        self._password = "clickhouse"

        self._network: Network | None = None
        self._keeper: DockerContainer | None = None
        self._nodes: list[DockerContainer] = []
        self._node_ports: list[int] = []
        self._config_dir: tempfile.TemporaryDirectory[str] | None = None

    def start(self) -> str:
        if self._nodes:
            return self.url(0)

        self._network = Network().create()

        try:
            self._start_keeper()
            self._start_nodes()
        except Exception:
            self.stop()
            raise

        return self.url(0)

    def stop(self) -> None:
        for node in self._nodes:
            with contextlib.suppress(Exception):
                node.stop()
        self._nodes = []
        self._node_ports = []

        if self._keeper is not None:
            with contextlib.suppress(Exception):
                self._keeper.stop()
            self._keeper = None

        if self._network is not None:
            with contextlib.suppress(Exception):
                self._network.remove()
            self._network = None

        if self._config_dir is not None:
            self._config_dir.cleanup()
            self._config_dir = None

    def reset(self) -> None:
        client = self._client(0)
        try:
            for (table,) in client.query("SHOW TABLES").result_rows:
                client.command(f"DROP TABLE IF EXISTS `{table}`")
        finally:
            client.close()

    def url(self, node: int = 0) -> str:
        host, port = self.host_port(node)
        return f"http://{self._user}:{self._password}@{host}:{port}/{self.database}"

    def version(self) -> str:
        return self.image.rsplit(":", 1)[-1]

    def diagnostics(self) -> dict[str, Any]:
        details: dict[str, Any] = {
            "image": self.image,
            "keeper_image": self.keeper_image,
            "version": self.version(),
            "database": self.database,
            "started": bool(self._nodes),
        }
        if self._network is not None:
            details["network_id"] = self._network.id
        if self._keeper is not None:
            details["keeper_container_id"] = self._keeper.get_container_id()
        for index, container in enumerate(self._nodes):
            details[f"node{index + 1}_container_id"] = container.get_container_id()
            details[f"node{index + 1}_host_port"] = self._node_ports[index]
        return details

    def _client(self, node: int = 0):
        import clickhouse_connect

        host, port = self.host_port(node)
        return clickhouse_connect.get_client(
            host=host,
            port=port,
            username=self._user,
            password=self._password,
            database=self.database,
        )

    def host_port(self, node: int = 0) -> tuple[str, int]:
        if not self._nodes or node >= len(self._nodes):
            raise RuntimeError("Provider is not started")
        container = self._nodes[node]
        return container.get_container_host_ip(), int(
            container.get_exposed_port(8123)
        )

    def _start_keeper(self) -> None:
        assert self._network is not None
        self._config_dir = tempfile.TemporaryDirectory(prefix="dbwarden-ch-")
        keeper_config_path = Path(self._config_dir.name) / "keeper_config.xml"
        keeper_config_path.write_text(self._keeper_config(), encoding="utf-8")

        self._keeper = (
            DockerContainer(self.keeper_image)
            .with_exposed_ports(9181)
            .with_volume_mapping(
                str(keeper_config_path),
                "/etc/clickhouse-keeper/keeper_config.xml",
                mode="ro",
            )
            .start()
        )
        self._network.connect(
            self._keeper.get_container_id(),
            network_aliases=["ch-keeper"],
        )
        self._wait_for_port(self._keeper, 9181)

    def _start_nodes(self) -> None:
        assert self._network is not None
        assert self._config_dir is not None

        for index, replica in enumerate(["ch-node1", "ch-node2"], start=1):
            config_path = Path(self._config_dir.name) / f"cluster-{index}.xml"
            config_path.write_text(self._cluster_config(replica), encoding="utf-8")

            container = (
                DockerContainer(self.image)
                .with_exposed_ports(8123)
                .with_env("CLICKHOUSE_DB", self.database)
                .with_env("CLICKHOUSE_USER", self._user)
                .with_env("CLICKHOUSE_PASSWORD", self._password)
                .with_env("CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT", "1")
                .with_volume_mapping(
                    str(config_path),
                    "/etc/clickhouse-server/config.d/cluster.xml",
                    mode="ro",
                )
                .start()
            )
            self._network.connect(
                container.get_container_id(),
                network_aliases=[replica],
            )
            self._nodes.append(container)
            self._node_ports.append(int(container.get_exposed_port(8123)))

        for node in range(len(self._nodes)):
            self._wait_for_node(node)

    def _wait_for_node(self, node: int, timeout: float = 60.0) -> None:
        container = self._nodes[node]
        self._wait_for_port(container, 8123, timeout=timeout)
        host, port = self.host_port(node)

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with contextlib.suppress(Exception), urllib.request.urlopen(
                f"http://{host}:{port}/ping", timeout=1.0
            ) as response:
                if response.read() == b"Ok.\n":
                    break
            time.sleep(0.2)
        else:
            raise TimeoutError(f"ClickHouse node {node + 1} HTTP ping did not respond")

        deadline = time.monotonic() + timeout
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            try:
                client = self._client(node)
                client.command("SELECT 1")
                client.close()
                return
            except Exception as error:  # noqa: BLE001
                last_error = error
                time.sleep(0.2)
        raise TimeoutError(f"ClickHouse node {node + 1} did not become ready") from last_error

    @staticmethod
    def _wait_for_port(
        container: DockerContainer, port: int, timeout: float = 60.0
    ) -> None:
        deadline = time.monotonic() + timeout
        host = container.get_container_host_ip()
        while time.monotonic() < deadline:
            mapped = int(container.get_exposed_port(port))
            try:
                with socket.create_connection((host, mapped), timeout=1.0):
                    return
            except OSError:
                time.sleep(0.5)
        raise TimeoutError(f"Port {port} did not become reachable on {host}")

    def _keeper_config(self) -> str:
        return """<clickhouse>
  <listen_host>0.0.0.0</listen_host>
  <logger>
    <level>information</level>
    <log>/var/log/clickhouse-keeper/clickhouse-keeper.log</log>
    <errorlog>/var/log/clickhouse-keeper/clickhouse-keeper.err.log</errorlog>
    <size>100M</size>
    <count>3</count>
  </logger>
  <max_connections>4096</max_connections>
  <keeper_server>
    <tcp_port>9181</tcp_port>
    <server_id>1</server_id>
    <log_storage_path>/var/lib/clickhouse/coordination/logs</log_storage_path>
    <snapshot_storage_path>/var/lib/clickhouse/coordination/snapshots</snapshot_storage_path>
    <coordination_settings>
      <operation_timeout_ms>10000</operation_timeout_ms>
      <min_session_timeout_ms>10000</min_session_timeout_ms>
      <session_timeout_ms>100000</session_timeout_ms>
    </coordination_settings>
    <raft_configuration>
      <server>
        <id>1</id>
        <hostname>localhost</hostname>
        <port>9234</port>
      </server>
    </raft_configuration>
  </keeper_server>
</clickhouse>
"""

    def _cluster_config(self, replica_name: str) -> str:
        return f"""<clickhouse>
  <remote_servers>
    <harness_cluster>
      <shard>
        <internal_replication>true</internal_replication>
        <replica>
          <host>ch-node1</host>
          <port>9000</port>
          <user>{self._user}</user>
          <password>{self._password}</password>
        </replica>
        <replica>
          <host>ch-node2</host>
          <port>9000</port>
          <user>{self._user}</user>
          <password>{self._password}</password>
        </replica>
      </shard>
    </harness_cluster>
  </remote_servers>
  <macros>
    <shard>01</shard>
    <replica>{replica_name}</replica>
  </macros>
  <zookeeper>
    <node>
      <host>ch-keeper</host>
      <port>9181</port>
    </node>
  </zookeeper>
</clickhouse>
"""
