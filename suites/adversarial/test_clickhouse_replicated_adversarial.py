from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import clickhouse_connect
import pytest

from infrastructure.providers import ClickHouseClusterProvider
from tools.migration_player import MigrationPlayer

pytestmark = pytest.mark.integration


def _cluster_client(provider: ClickHouseClusterProvider, node: int = 0):
    """Build a clickhouse_connect client from a provider node's mapped URL."""
    url = urlparse(provider.url(node))
    return clickhouse_connect.get_client(
        host=url.hostname or "localhost",
        port=url.port or 8123,
        username=url.username or "clickhouse",
        password=url.password or "clickhouse",
        database=url.path.lstrip("/") or "harness",
    )


def _write_migration(
    player: MigrationPlayer,
    version: int,
    upgrade: str,
    rollback: str,
) -> Path:
    """Write a raw SQL migration file for dbwarden to apply via node 0."""
    directory = player.work_dir / "migrations" / "primary"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"primary__{version:04d}__replicated.sql"
    path.write_text(
        f"-- upgrade\n{upgrade}\n-- rollback\n{rollback}\n",
        encoding="utf-8",
    )
    return path


def _table_engine(
    provider: ClickHouseClusterProvider, node: int, table: str
) -> str:
    client = _cluster_client(provider, node)
    try:
        result = client.query(
            "SELECT engine FROM system.tables "
            "WHERE database = currentDatabase() AND name = {table:String}",
            parameters={"table": table},
        )
        rows = result.result_rows
        if not rows:
            raise AssertionError(f"Table {table!r} not found on node {node}")
        return rows[0][0]
    finally:
        client.close()


def _replica_row(
    provider: ClickHouseClusterProvider, table: str, node: int = 0
) -> tuple[str, int]:
    """Return (zookeeper_path, is_readonly) for a replicated table."""
    client = _cluster_client(provider, node)
    try:
        result = client.query(
            "SELECT zookeeper_path, is_readonly FROM system.replicas "
            "WHERE table = {table:String}",
            parameters={"table": table},
        )
        rows = result.result_rows
        if not rows:
            raise AssertionError(f"No replica entry for {table!r} on node {node}")
        return rows[0][0], rows[0][1]
    finally:
        client.close()


def _wait_for_count(
    provider: ClickHouseClusterProvider,
    table: str,
    expected: int,
    node: int = 1,
    timeout: float = 60.0,
) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        client = _cluster_client(provider, node)
        try:
            count = client.query(f"SELECT count() FROM {table}").result_rows[0][0]
            if count == expected:
                return
        except Exception as error:  # noqa: BLE001
            last_error = error
        finally:
            client.close()
        time.sleep(0.5)
    raise TimeoutError(
        f"Table {table!r} on node {node} did not reach {expected} rows"
    ) from last_error


def _insert_events(provider: ClickHouseClusterProvider, count: int = 3) -> None:
    client = _cluster_client(provider, 0)
    try:
        rows = [
            (index, datetime(2024, 1, 1, tzinfo=UTC), f"event-{uuid.uuid4().hex[:6]}", index, float(index))
            for index in range(count)
        ]
        client.insert("events", rows, column_names=["id", "occurred_at", "event_name", "user_id", "value"])
    finally:
        client.close()


@pytest.fixture
def cluster():
    provider = ClickHouseClusterProvider()
    try:
        provider.start()
        yield provider
    finally:
        provider.stop()


def test_mergetree_to_replicated_mergetree(cluster: ClickHouseClusterProvider, tmp_path: Path):
    player = MigrationPlayer(cluster.url(0), tmp_path)
    player.init_and_configure(database_type="clickhouse")

    _write_migration(
        player,
        1,
        "CREATE TABLE events ON CLUSTER 'harness_cluster' ("
        "    id Int32,"
        "    occurred_at DateTime,"
        "    event_name String,"
        "    user_id Int32,"
        "    value Float64"
        ") ENGINE = MergeTree() ORDER BY (occurred_at, id);",
        "DROP TABLE IF EXISTS events ON CLUSTER 'harness_cluster';",
    )
    player.migrate()

    _insert_events(cluster, count=3)

    _write_migration(
        player,
        2,
        "CREATE TABLE events_new ON CLUSTER 'harness_cluster' ("
        "    id Int32,"
        "    occurred_at DateTime,"
        "    event_name String,"
        "    user_id Int32,"
        "    value Float64"
        ") ENGINE = ReplicatedMergeTree('/clickhouse/tables/{shard}/events', '{replica}') "
        "ORDER BY (occurred_at, id);\n"
        "INSERT INTO events_new SELECT * FROM events;\n"
        "DROP TABLE IF EXISTS events ON CLUSTER 'harness_cluster';\n"
        "RENAME TABLE events_new TO events ON CLUSTER 'harness_cluster';",
        "DROP TABLE IF EXISTS events ON CLUSTER 'harness_cluster';",
    )
    player.migrate()

    assert _table_engine(cluster, 0, "events") == "ReplicatedMergeTree"
    zookeeper_path, is_readonly = _replica_row(cluster, "events", node=0)
    assert zookeeper_path.startswith("/clickhouse/tables/")
    assert zookeeper_path.endswith("/events")
    assert is_readonly == 0
    _wait_for_count(cluster, "events", expected=3, node=1)


def test_replicated_mergetree_to_replicated_replacing(cluster: ClickHouseClusterProvider, tmp_path: Path):
    player = MigrationPlayer(cluster.url(0), tmp_path)
    player.init_and_configure(database_type="clickhouse")

    _write_migration(
        player,
        1,
        "CREATE TABLE events ON CLUSTER 'harness_cluster' ("
        "    id Int32,"
        "    occurred_at DateTime,"
        "    event_name String,"
        "    user_id Int32,"
        "    value Float64"
        ") ENGINE = ReplicatedMergeTree('/clickhouse/tables/{shard}/events', '{replica}') "
        "ORDER BY (occurred_at, id);",
        "DROP TABLE IF EXISTS events ON CLUSTER 'harness_cluster';",
    )
    player.migrate()

    _insert_events(cluster, count=5)

    _write_migration(
        player,
        2,
        "CREATE TABLE events_new ON CLUSTER 'harness_cluster' ("
        "    id Int32,"
        "    occurred_at DateTime,"
        "    event_name String,"
        "    user_id Int32,"
        "    value Float64"
        ") ENGINE = ReplicatedReplacingMergeTree('/clickhouse/tables/{shard}/events_v2', '{replica}') "
        "ORDER BY (occurred_at, id);\n"
        "INSERT INTO events_new SELECT * FROM events;\n"
        "DROP TABLE IF EXISTS events ON CLUSTER 'harness_cluster';\n"
        "RENAME TABLE events_new TO events ON CLUSTER 'harness_cluster';",
        "DROP TABLE IF EXISTS events ON CLUSTER 'harness_cluster';",
    )
    player.migrate()

    assert _table_engine(cluster, 0, "events") == "ReplicatedReplacingMergeTree"
    zookeeper_path, is_readonly = _replica_row(cluster, "events", node=0)
    assert zookeeper_path.startswith("/clickhouse/tables/")
    assert zookeeper_path.endswith("/events_v2")
    assert is_readonly == 0
    _wait_for_count(cluster, "events", expected=5, node=1)


def test_replicated_materialized_view(cluster: ClickHouseClusterProvider, tmp_path: Path):
    player = MigrationPlayer(cluster.url(0), tmp_path)
    player.init_and_configure(database_type="clickhouse")

    _write_migration(
        player,
        1,
        "CREATE TABLE events ON CLUSTER 'harness_cluster' ("
        "    id Int32,"
        "    event_name String,"
        "    value Float64"
        ") ENGINE = ReplicatedMergeTree('/clickhouse/tables/{shard}/events', '{replica}') ORDER BY id;\n"
        "CREATE TABLE event_totals ON CLUSTER 'harness_cluster' ("
        "    event_name String,"
        "    total Float64"
        ") ENGINE = ReplicatedMergeTree('/clickhouse/tables/{shard}/event_totals', '{replica}') ORDER BY event_name;",
        "DROP TABLE IF EXISTS events_mv ON CLUSTER 'harness_cluster';\n"
        "DROP TABLE IF EXISTS event_totals ON CLUSTER 'harness_cluster';\n"
        "DROP TABLE IF EXISTS events ON CLUSTER 'harness_cluster';",
    )
    player.migrate()

    _write_migration(
        player,
        2,
        "CREATE MATERIALIZED VIEW events_mv ON CLUSTER 'harness_cluster' "
        "TO event_totals AS SELECT event_name, sum(value) AS total FROM events GROUP BY event_name;",
        "DROP TABLE IF EXISTS events_mv ON CLUSTER 'harness_cluster';",
    )
    player.migrate()

    client = _cluster_client(cluster, 0)
    try:
        client.insert(
            "events",
            [(1, "signup", 10.0), (2, "signup", 20.0), (3, "login", 5.0)],
            column_names=["id", "event_name", "value"],
        )
    finally:
        client.close()

    assert _table_engine(cluster, 1, "events_mv") == "MaterializedView"
    _wait_for_count(cluster, "event_totals", expected=2, node=1)


def test_on_cluster_propagation(cluster: ClickHouseClusterProvider, tmp_path: Path):
    player = MigrationPlayer(cluster.url(0), tmp_path)
    player.init_and_configure(database_type="clickhouse")

    _write_migration(
        player,
        1,
        "CREATE TABLE distributed_test ON CLUSTER 'harness_cluster' ("
        "    id Int32,"
        "    payload String"
        ") ENGINE = MergeTree() ORDER BY id;",
        "DROP TABLE IF EXISTS distributed_test ON CLUSTER 'harness_cluster';",
    )
    player.migrate()

    node1_client = _cluster_client(cluster, 1)
    try:
        result = node1_client.query(
            "SELECT count() FROM system.tables "
            "WHERE database = currentDatabase() AND name = 'distributed_test'"
        )
        assert result.result_rows[0][0] == 1
    finally:
        node1_client.close()


def test_keeper_path_change(cluster: ClickHouseClusterProvider, tmp_path: Path):
    player = MigrationPlayer(cluster.url(0), tmp_path)
    player.init_and_configure(database_type="clickhouse")

    _write_migration(
        player,
        1,
        "CREATE TABLE events ON CLUSTER 'harness_cluster' ("
        "    id Int32,"
        "    occurred_at DateTime,"
        "    event_name String,"
        "    user_id Int32,"
        "    value Float64"
        ") ENGINE = ReplicatedMergeTree('/clickhouse/tables/old/events', '{replica}') "
        "ORDER BY (occurred_at, id);",
        "DROP TABLE IF EXISTS events ON CLUSTER 'harness_cluster';",
    )
    player.migrate()

    _insert_events(cluster, count=4)

    _write_migration(
        player,
        2,
        "CREATE TABLE events_new ON CLUSTER 'harness_cluster' ("
        "    id Int32,"
        "    occurred_at DateTime,"
        "    event_name String,"
        "    user_id Int32,"
        "    value Float64"
        ") ENGINE = ReplicatedMergeTree('/clickhouse/tables/new/events', '{replica}') "
        "ORDER BY (occurred_at, id);\n"
        "INSERT INTO events_new SELECT * FROM events;\n"
        "DROP TABLE IF EXISTS events ON CLUSTER 'harness_cluster';\n"
        "RENAME TABLE events_new TO events ON CLUSTER 'harness_cluster';",
        "DROP TABLE IF EXISTS events ON CLUSTER 'harness_cluster';",
    )
    player.migrate()

    node0_client = _cluster_client(cluster, 0)
    try:
        paths = {
            row[0]
            for row in node0_client.query(
                "SELECT zookeeper_path FROM system.replicas WHERE table = 'events'"
            ).result_rows
        }
        assert "/clickhouse/tables/old/events" not in paths
        assert "/clickhouse/tables/new/events" in paths
    finally:
        node0_client.close()

    _wait_for_count(cluster, "events", expected=4, node=1)
