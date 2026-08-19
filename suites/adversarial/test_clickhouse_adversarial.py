from pathlib import Path
from urllib.parse import parse_qs, urlparse

import clickhouse_connect
import pytest

from infrastructure.providers import provider_for
from tools.drift_checker import DriftChecker
from tools.migration_player import MigrationPlayer


def _write_migration(directory: Path, number: int, upgrade: str, rollback: str) -> None:
    (directory / f"primary__{number:04d}_evolution.sql").write_text(
        f"-- upgrade\n{upgrade}\n-- rollback\n{rollback}\n",
        encoding="utf-8",
    )


def _migration_dir(player: MigrationPlayer) -> Path:
    path = player.work_dir / "migrations" / "primary"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _clickhouse_client(database_url: str):
    parsed = urlparse(database_url)
    query = parse_qs(parsed.query)
    return clickhouse_connect.get_client(
        host=parsed.hostname or "localhost",
        port=parsed.port or 8123,
        username=parsed.username or "default",
        password=parsed.password or "",
        database=parsed.path.lstrip("/") or "default",
        secure=parsed.scheme == "https",
        **{key: values[-1] for key, values in query.items()},
    )


def _row_count(client, table: str) -> int:
    return client.query(f"SELECT count() FROM {table}").result_rows[0][0]


def _partition_ids(client, table: str) -> tuple[str, ...]:
    rows = client.query(
        "SELECT partition_id FROM system.parts "
        "WHERE database = currentDatabase() AND table = %(table)s AND active = 1",
        parameters={"table": table},
    ).result_rows
    return tuple(sorted({row[0] for row in rows}))


def _column_codec(client, table: str, column: str) -> str:
    create_query = client.command(f"SHOW CREATE TABLE {table}")
    return create_query or ""


def _projection_exists(client, table: str, projection: str) -> bool:
    rows = client.query(
        "SELECT name FROM system.projections "
        "WHERE database = currentDatabase() AND table = %(table)s AND name = %(projection)s",
        parameters={"table": table, "projection": projection},
    ).result_rows
    return bool(rows)


def _projection_part_count(client, table: str, projection: str) -> int:
    rows = client.query(
        "SELECT count() FROM system.projection_parts "
        "WHERE database = currentDatabase() AND table = %(table)s "
        "AND name = %(projection)s AND active = 1",
        parameters={"table": table, "projection": projection},
    ).result_rows
    return rows[0][0]


@pytest.fixture
def clickhouse_player(tmp_path: Path) -> MigrationPlayer:
    provider = provider_for("clickhouse", "26.6")
    try:
        player = MigrationPlayer(provider.start(), tmp_path)
        player.init_and_configure(database_type="clickhouse")
        yield player
    finally:
        provider.stop()


@pytest.mark.integration
def test_order_by_change(clickhouse_player: MigrationPlayer):
    player = clickhouse_player
    migration_dir = _migration_dir(player)
    _write_migration(
        migration_dir,
        1,
        "CREATE TABLE events (id Int64, ts DateTime) ENGINE = MergeTree ORDER BY (ts, id);",
        "DROP TABLE events;",
    )
    assert player.migrate().returncode == 0

    client = _clickhouse_client(player.database_url)
    client.command(
        "INSERT INTO events VALUES (1, '2024-01-01 00:00:00'), (2, '2024-01-02 00:00:00')"
    )

    original_key = dict(
        DriftChecker().capture(player.database_url).table_options["events"]
    )["sorting_key"]

    _write_migration(
        migration_dir,
        2,
        "CREATE TABLE events_new (id Int64, ts DateTime) ENGINE = MergeTree ORDER BY (id, ts);\n"
        "INSERT INTO events_new SELECT * FROM events;\n"
        "RENAME TABLE events TO events_old, events_new TO events;\n"
        "DROP TABLE events_old;",
        "CREATE TABLE events_new (id Int64, ts DateTime) ENGINE = MergeTree ORDER BY (ts, id);\n"
        "INSERT INTO events_new SELECT * FROM events;\n"
        "RENAME TABLE events TO events_old, events_new TO events;\n"
        "DROP TABLE events_old;",
    )
    assert player.migrate().returncode == 0

    snapshot = DriftChecker().capture(player.database_url)
    new_key = dict(snapshot.table_options["events"])["sorting_key"]
    assert new_key != original_key
    assert _row_count(client, "events") == 2

    assert player.rollback().returncode == 0
    rolled_key = dict(DriftChecker().capture(player.database_url).table_options["events"])[
        "sorting_key"
    ]
    assert rolled_key == original_key
    assert _row_count(client, "events") == 2


@pytest.mark.integration
def test_partition_by_change(clickhouse_player: MigrationPlayer):
    player = clickhouse_player
    migration_dir = _migration_dir(player)
    _write_migration(
        migration_dir,
        1,
        "CREATE TABLE events (id Int64, ts DateTime) ENGINE = MergeTree "
        "ORDER BY id PARTITION BY toYYYYMM(ts);",
        "DROP TABLE events;",
    )
    assert player.migrate().returncode == 0

    client = _clickhouse_client(player.database_url)
    client.command(
        "INSERT INTO events VALUES (1, '2024-01-01 00:00:00'), (2, '2024-01-02 00:00:00')"
    )

    original_key = dict(
        DriftChecker().capture(player.database_url).table_options["events"]
    )["partition_key"]
    original_parts = _partition_ids(client, "events")

    _write_migration(
        migration_dir,
        2,
        "CREATE TABLE events_new (id Int64, ts DateTime) ENGINE = MergeTree "
        "ORDER BY id PARTITION BY toDate(ts);\n"
        "INSERT INTO events_new SELECT * FROM events;\n"
        "RENAME TABLE events TO events_old, events_new TO events;\n"
        "DROP TABLE events_old;",
        "CREATE TABLE events_new (id Int64, ts DateTime) ENGINE = MergeTree "
        "ORDER BY id PARTITION BY toYYYYMM(ts);\n"
        "INSERT INTO events_new SELECT * FROM events;\n"
        "RENAME TABLE events TO events_old, events_new TO events;\n"
        "DROP TABLE events_old;",
    )
    assert player.migrate().returncode == 0

    snapshot = DriftChecker().capture(player.database_url)
    new_key = dict(snapshot.table_options["events"])["partition_key"]
    assert new_key != original_key
    new_parts = _partition_ids(client, "events")
    assert len(new_parts) > len(original_parts)
    assert _row_count(client, "events") == 2


@pytest.mark.integration
def test_codec_change(clickhouse_player: MigrationPlayer):
    player = clickhouse_player
    migration_dir = _migration_dir(player)
    _write_migration(
        migration_dir,
        1,
        "CREATE TABLE codec_demo (id UInt64, payload String) ENGINE = MergeTree ORDER BY id;",
        "DROP TABLE codec_demo;",
    )
    assert player.migrate().returncode == 0

    client = _clickhouse_client(player.database_url)
    client.command("INSERT INTO codec_demo VALUES (1, 'hello'), (2, 'world')")

    _write_migration(
        migration_dir,
        2,
        "ALTER TABLE codec_demo MODIFY COLUMN payload String CODEC(ZSTD(1));",
        "ALTER TABLE codec_demo MODIFY COLUMN payload String CODEC(Default);",
    )
    assert player.migrate().returncode == 0
    assert "ZSTD" in _column_codec(client, "codec_demo", "payload").upper()

    assert player.rollback().returncode == 0
    assert "ZSTD" not in _column_codec(client, "codec_demo", "payload").upper()


@pytest.mark.integration
def test_projection_change(clickhouse_player: MigrationPlayer):
    player = clickhouse_player
    migration_dir = _migration_dir(player)
    _write_migration(
        migration_dir,
        1,
        "CREATE TABLE orders (id UInt64, amount Decimal(10, 2)) ENGINE = MergeTree ORDER BY id;",
        "DROP TABLE orders;",
    )
    assert player.migrate().returncode == 0

    client = _clickhouse_client(player.database_url)
    _write_migration(
        migration_dir,
        2,
        "ALTER TABLE orders ADD PROJECTION orders_by_amount (SELECT id ORDER BY amount);",
        "ALTER TABLE orders DROP PROJECTION orders_by_amount;",
    )
    assert player.migrate().returncode == 0
    assert _projection_exists(client, "orders", "orders_by_amount")

    client.command("INSERT INTO orders VALUES (1, 10.00), (2, 5.00), (3, 20.00)")
    assert _projection_part_count(client, "orders", "orders_by_amount") > 0

    explain_rows = client.query("EXPLAIN SELECT id FROM orders ORDER BY amount").result_rows
    explain_text = "\n".join(str(row[0]) for row in explain_rows)
    assert "orders_by_amount" in explain_text

    assert player.rollback().returncode == 0
    assert not _projection_exists(client, "orders", "orders_by_amount")


@pytest.mark.integration
def test_materialized_view_select_change(clickhouse_player: MigrationPlayer):
    player = clickhouse_player
    migration_dir = _migration_dir(player)
    _write_migration(
        migration_dir,
        1,
        "CREATE TABLE clicks (id UInt64, url String) ENGINE = MergeTree ORDER BY id;\n"
        "CREATE TABLE mv_target_a (id UInt64, url_len UInt64) ENGINE = MergeTree ORDER BY id;\n"
        "CREATE MATERIALIZED VIEW mv_clicks TO mv_target_a "
        "AS SELECT id, length(url) AS url_len FROM clicks;",
        "DROP TABLE IF EXISTS mv_clicks;\n"
        "DROP TABLE IF EXISTS mv_target_a;\n"
        "DROP TABLE clicks;",
    )
    assert player.migrate().returncode == 0

    client = _clickhouse_client(player.database_url)
    client.command("INSERT INTO clicks VALUES (1, 'http://a'), (2, 'http://bb')")
    assert _row_count(client, "mv_target_a") == 2

    _write_migration(
        migration_dir,
        2,
        "DROP TABLE IF EXISTS mv_clicks;\n"
        "CREATE TABLE mv_target_b (id UInt64, url String) ENGINE = MergeTree ORDER BY id;\n"
        "CREATE MATERIALIZED VIEW mv_clicks TO mv_target_b AS SELECT id, url FROM clicks;",
        "DROP TABLE IF EXISTS mv_clicks;\n"
        "DROP TABLE IF EXISTS mv_target_b;\n"
        "CREATE MATERIALIZED VIEW mv_clicks TO mv_target_a "
        "AS SELECT id, length(url) AS url_len FROM clicks;",
    )
    assert player.migrate().returncode == 0

    client.command("INSERT INTO clicks VALUES (3, 'http://ccc'), (4, 'http://dddd')")
    target_b_rows = client.query("SELECT id, url FROM mv_target_b ORDER BY id").result_rows
    assert target_b_rows == [(3, "http://ccc"), (4, "http://dddd")]

    target_a_rows = client.query("SELECT id, url_len FROM mv_target_a ORDER BY id").result_rows
    assert target_a_rows == [(1, 8), (2, 9)]


@pytest.mark.integration
def test_materialized_view_target_change(clickhouse_player: MigrationPlayer):
    player = clickhouse_player
    migration_dir = _migration_dir(player)
    _write_migration(
        migration_dir,
        1,
        "CREATE TABLE clicks (id UInt64, url String) ENGINE = MergeTree ORDER BY id;\n"
        "CREATE TABLE target_a (id UInt64, url String) ENGINE = MergeTree ORDER BY id;\n"
        "CREATE TABLE target_b (id UInt64, url String) ENGINE = MergeTree ORDER BY id;\n"
        "CREATE MATERIALIZED VIEW mv_clicks TO target_a AS SELECT id, url FROM clicks;",
        "DROP TABLE IF EXISTS mv_clicks;\n"
        "DROP TABLE target_b;\n"
        "DROP TABLE target_a;\n"
        "DROP TABLE clicks;",
    )
    assert player.migrate().returncode == 0

    client = _clickhouse_client(player.database_url)
    client.command("INSERT INTO clicks VALUES (1, 'a'), (2, 'b')")
    assert _row_count(client, "target_a") == 2
    assert _row_count(client, "target_b") == 0

    _write_migration(
        migration_dir,
        2,
        "DROP TABLE IF EXISTS mv_clicks;\n"
        "CREATE MATERIALIZED VIEW mv_clicks TO target_b AS SELECT id, url FROM clicks;",
        "DROP TABLE IF EXISTS mv_clicks;\n"
        "CREATE MATERIALIZED VIEW mv_clicks TO target_a AS SELECT id, url FROM clicks;",
    )
    assert player.migrate().returncode == 0

    client.command("INSERT INTO clicks VALUES (3, 'c'), (4, 'd')")
    assert _row_count(client, "target_a") == 2
    assert _row_count(client, "target_b") == 2
    target_b_rows = client.query("SELECT id, url FROM target_b ORDER BY id").result_rows
    assert target_b_rows == [(3, "c"), (4, "d")]


@pytest.mark.integration
def test_engine_recreation_with_existing_data(clickhouse_player: MigrationPlayer):
    player = clickhouse_player
    migration_dir = _migration_dir(player)
    _write_migration(
        migration_dir,
        1,
        "CREATE TABLE vehicles (id UInt64, name String) ENGINE = MergeTree ORDER BY id;",
        "DROP TABLE vehicles;",
    )
    assert player.migrate().returncode == 0

    client = _clickhouse_client(player.database_url)
    client.command("INSERT INTO vehicles VALUES (1, 'a'), (2, 'b')")

    _write_migration(
        migration_dir,
        2,
        "CREATE TABLE vehicles_new (id UInt64, name String) ENGINE = ReplacingMergeTree ORDER BY id;\n"
        "INSERT INTO vehicles_new SELECT * FROM vehicles;\n"
        "RENAME TABLE vehicles TO vehicles_old, vehicles_new TO vehicles;\n"
        "DROP TABLE vehicles_old;",
        "CREATE TABLE vehicles_new (id UInt64, name String) ENGINE = MergeTree ORDER BY id;\n"
        "INSERT INTO vehicles_new SELECT * FROM vehicles;\n"
        "RENAME TABLE vehicles TO vehicles_old, vehicles_new TO vehicles;\n"
        "DROP TABLE vehicles_old;",
    )
    assert player.migrate().returncode == 0

    engine = dict(DriftChecker().capture(player.database_url).table_options["vehicles"])["engine"]
    assert engine == "ReplacingMergeTree"
    assert _row_count(client, "vehicles") == 2


@pytest.mark.integration
def test_engine_recreation_with_rollback(clickhouse_player: MigrationPlayer):
    player = clickhouse_player
    migration_dir = _migration_dir(player)
    _write_migration(
        migration_dir,
        1,
        "CREATE TABLE vehicles (id UInt64, name String) ENGINE = MergeTree ORDER BY id;",
        "DROP TABLE vehicles;",
    )
    assert player.migrate().returncode == 0

    client = _clickhouse_client(player.database_url)
    client.command("INSERT INTO vehicles VALUES (1, 'a'), (2, 'b')")

    _write_migration(
        migration_dir,
        2,
        "CREATE TABLE vehicles_new (id UInt64, name String) ENGINE = ReplacingMergeTree ORDER BY id;\n"
        "INSERT INTO vehicles_new SELECT * FROM vehicles;\n"
        "RENAME TABLE vehicles TO vehicles_old, vehicles_new TO vehicles;\n"
        "DROP TABLE vehicles_old;",
        "CREATE TABLE vehicles_new (id UInt64, name String) ENGINE = MergeTree ORDER BY id;\n"
        "INSERT INTO vehicles_new SELECT * FROM vehicles;\n"
        "RENAME TABLE vehicles TO vehicles_old, vehicles_new TO vehicles;\n"
        "DROP TABLE vehicles_old;",
    )
    assert player.migrate().returncode == 0
    engine = dict(DriftChecker().capture(player.database_url).table_options["vehicles"])["engine"]
    assert engine == "ReplacingMergeTree"
    assert _row_count(client, "vehicles") == 2

    assert player.rollback().returncode == 0
    rolled_engine = dict(DriftChecker().capture(player.database_url).table_options["vehicles"])[
        "engine"
    ]
    assert rolled_engine == "MergeTree"
    assert _row_count(client, "vehicles") == 2


@pytest.mark.integration
def test_partially_failed_recreate(clickhouse_player: MigrationPlayer):
    player = clickhouse_player
    migration_dir = _migration_dir(player)
    _write_migration(
        migration_dir,
        1,
        "CREATE TABLE fragile (id UInt64) ENGINE = MergeTree ORDER BY id;",
        "DROP TABLE fragile;",
    )
    assert player.migrate().returncode == 0

    client = _clickhouse_client(player.database_url)
    client.command("INSERT INTO fragile VALUES (1), (2)")

    _write_migration(
        migration_dir,
        2,
        "CREATE TABLE fragile_new (id UInt64, extra String) ENGINE = MergeTree ORDER BY id;\n"
        "INSERT INTO fragile_new SELECT id, nonexistent FROM fragile;\n"
        "DROP TABLE fragile;",
        "DROP TABLE IF EXISTS fragile_new;",
    )
    result = player.cli.run("migrate", clean=False, check=False)
    assert result.returncode != 0
    assert "nonexistent" in result.output.lower()

    history = player.cli.run("history", clean=False, check=False).plain_output
    assert "0002" not in history

    _write_migration(
        migration_dir,
        2,
        "DROP TABLE IF EXISTS fragile_new;\n"
        "CREATE TABLE fragile_new (id UInt64) ENGINE = MergeTree ORDER BY id;\n"
        "INSERT INTO fragile_new SELECT id FROM fragile;\n"
        "RENAME TABLE fragile TO fragile_old, fragile_new TO fragile;\n"
        "DROP TABLE fragile_old;",
        "DROP TABLE IF EXISTS fragile_new;",
    )
    assert player.migrate().returncode == 0
    player.assert_converged()
    assert _row_count(client, "fragile") == 2
