from __future__ import annotations

import contextlib
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

import clickhouse_connect
import pytest
from sqlalchemy import create_engine, text

from infrastructure.providers import provider_for
from tools.drift_checker import DriftChecker
from tools.migration_player import MigrationPlayer


def _write_migration(directory: Path, number: int, upgrade: str, rollback: str) -> None:
    (directory / f"primary__{number:04d}_safety.sql").write_text(
        f"-- upgrade\n{upgrade}\n-- rollback\n{rollback}\n",
        encoding="utf-8",
    )


def _pg_engine(database_url: str):
    return create_engine(database_url, pool_pre_ping=True)


def _ch_client(database_url: str):
    parsed = urlparse(database_url)
    return clickhouse_connect.get_client(
        host=parsed.hostname or "localhost",
        port=parsed.port or 8123,
        username=parsed.username or "default",
        password=parsed.password or "",
        database=parsed.path.lstrip("/") or "default",
    )


@pytest.mark.integration
def test_postgres_add_column_does_not_block_workload(tmp_path: Path):
    """Adding a nullable column in PostgreSQL 11+ is metadata-only and must not
    stall concurrent readers/writers.
    """
    provider = provider_for("postgres", "17")
    try:
        player = MigrationPlayer(provider.start(), tmp_path)
        player.init_and_configure(database_type="postgresql")
        migration_dir = tmp_path / "migrations" / "primary"
        migration_dir.mkdir(parents=True, exist_ok=True)
        _write_migration(
            migration_dir,
            1,
            "CREATE TABLE load_test (id BIGINT PRIMARY KEY, payload TEXT NOT NULL);"
            "INSERT INTO load_test (id, payload) SELECT generate_series(1, 1000), 'x';",
            "DROP TABLE load_test;",
        )
        _write_migration(
            migration_dir,
            2,
            "ALTER TABLE load_test ADD COLUMN score INTEGER;",
            "ALTER TABLE load_test DROP COLUMN score;",
        )

        assert player.migrate().returncode == 0

        engine = _pg_engine(player.database_url)
        stop_event = threading.Event()
        latencies: list[float] = []
        errors: list[str] = []

        def workload():
            while not stop_event.is_set():
                start = time.monotonic()
                try:
                    with engine.connect() as conn:
                        conn.execute(text("SELECT COUNT(*) FROM load_test"))
                        conn.execute(
                            text("INSERT INTO load_test (id, payload) VALUES (:id, :payload)"),
                            {"id": 10000 + int(time.monotonic() * 1000), "payload": "y"},
                        )
                        conn.commit()
                except Exception as exc:  # noqa: BLE001
                    errors.append(str(exc))
                else:
                    latencies.append(time.monotonic() - start)
                time.sleep(0.02)

        worker = threading.Thread(target=workload)
        worker.start()
        time.sleep(0.2)  # warm-up

        result = player.migrate()
        stop_event.set()
        worker.join(timeout=10)

        assert result.returncode == 0, result.output
        assert not errors, f"Concurrent queries failed: {errors[:5]}"
        assert latencies, "No latency samples collected"
        max_latency = max(latencies)
        assert max_latency < 1.0, f"Add-column migration stalled queries for {max_latency:.3f}s"

        snapshot = DriftChecker().capture(player.database_url)
        assert "score" in snapshot.columns["load_test"]
    finally:
        provider.stop()


@pytest.mark.integration
def test_postgres_create_index_lock_classification(tmp_path: Path):
    """CREATE INDEX (without CONCURRENTLY) must take a Share lock, not an
    AccessExclusiveLock, so reads continue but writes are blocked.  This test
    codifies the lock class so regressions to more aggressive locking are caught.
    """
    provider = provider_for("postgres", "17")
    try:
        player = MigrationPlayer(provider.start(), tmp_path)
        player.init_and_configure(database_type="postgresql")
        migration_dir = tmp_path / "migrations" / "primary"
        migration_dir.mkdir(parents=True, exist_ok=True)
        _write_migration(
            migration_dir,
            1,
            "CREATE TABLE indexed (id INTEGER PRIMARY KEY, value TEXT);"
            "INSERT INTO indexed SELECT generate_series(1, 100), 'v';",
            "DROP TABLE indexed;",
        )
        _write_migration(
            migration_dir,
            2,
            "CREATE INDEX idx_indexed_value ON indexed(value);",
            "DROP INDEX idx_indexed_value;",
        )

        engine = _pg_engine(player.database_url)
        lock_mode: list[str] = []

        def observe_lock():
            deadline = time.monotonic() + 10.0
            while time.monotonic() < deadline:
                with contextlib.suppress(Exception), engine.connect() as conn:
                    rows = conn.execute(
                        text(
                            "SELECT mode FROM pg_locks "
                            "WHERE relation = 'indexed'::regclass AND locktype = 'relation'"
                        )
                    ).fetchall()
                    lock_mode.extend(row[0] for row in rows)
                time.sleep(0.02)

        observer = threading.Thread(target=observe_lock)
        observer.start()
        result = player.migrate()
        observer.join(timeout=15)

        assert result.returncode == 0, result.output
        unique_modes = set(lock_mode)
        assert "ShareLock" in unique_modes, f"Expected ShareLock, observed {unique_modes}"
        assert "AccessExclusiveLock" not in unique_modes, (
            f"CREATE INDEX unexpectedly took AccessExclusiveLock: {unique_modes}"
        )
    finally:
        provider.stop()


@pytest.mark.integration
def test_clickhouse_add_column_stays_online(tmp_path: Path):
    """ALTER TABLE ADD COLUMN on ClickHouse MergeTree must not fail concurrent
    SELECT/INSERT or stall them beyond a short threshold.
    """
    provider = provider_for("clickhouse", "26.6")
    try:
        player = MigrationPlayer(provider.start(), tmp_path)
        player.init_and_configure(database_type="clickhouse")
        migration_dir = tmp_path / "migrations" / "primary"
        migration_dir.mkdir(parents=True, exist_ok=True)
        _write_migration(
            migration_dir,
            1,
            "CREATE TABLE load_test (id UInt64, payload String) ENGINE = MergeTree ORDER BY id;"
            "INSERT INTO load_test SELECT number, toString(number) FROM numbers(1000);",
            "DROP TABLE load_test;",
        )
        _write_migration(
            migration_dir,
            2,
            "ALTER TABLE load_test ADD COLUMN score UInt64 DEFAULT 0;",
            "ALTER TABLE load_test DROP COLUMN score;",
        )

        assert player.migrate().returncode == 0

        stop_event = threading.Event()
        latencies: list[float] = []
        errors: list[str] = []

        def workload():
            counter = 0
            while not stop_event.is_set():
                start = time.monotonic()
                client = _ch_client(player.database_url)
                try:
                    client.query("SELECT COUNT() FROM load_test")
                    client.insert(
                        "load_test",
                        [[10000 + counter, "y"]],
                        column_names=["id", "payload"],
                    )
                except Exception as exc:  # noqa: BLE001
                    errors.append(str(exc))
                else:
                    latencies.append(time.monotonic() - start)
                finally:
                    client.close()
                counter += 1
                time.sleep(0.02)

        worker = threading.Thread(target=workload)
        worker.start()
        time.sleep(0.2)

        result = player.migrate()
        stop_event.set()
        worker.join(timeout=10)

        assert result.returncode == 0, result.output
        assert not errors, f"Concurrent queries failed: {errors[:5]}"
        assert latencies, "No latency samples collected"
        max_latency = max(latencies)
        assert max_latency < 2.0, f"Add-column migration stalled queries for {max_latency:.3f}s"

        snapshot = DriftChecker().capture(player.database_url)
        assert "score" in snapshot.columns["load_test"]
    finally:
        provider.stop()


@pytest.mark.integration
def test_clickhouse_engine_recreate_documents_downtime(tmp_path: Path):
    """The ClickHouse engine-recreation pattern briefly renames tables away.
    This test documents that concurrent reads will observe failures during the
    rename window, and that the migration completes with data intact.
    """
    provider = provider_for("clickhouse", "26.6")
    try:
        player = MigrationPlayer(provider.start(), tmp_path)
        player.init_and_configure(database_type="clickhouse")
        migration_dir = tmp_path / "migrations" / "primary"
        migration_dir.mkdir(parents=True, exist_ok=True)
        _write_migration(
            migration_dir,
            1,
            "CREATE TABLE recreate_test (id UInt64, payload String) ENGINE = MergeTree ORDER BY id;"
            "INSERT INTO recreate_test SELECT number, toString(number) FROM numbers(100);",
            "DROP TABLE recreate_test;",
        )
        _write_migration(
            migration_dir,
            2,
            "CREATE TABLE recreate_test_new (id UInt64, payload String) ENGINE = ReplacingMergeTree ORDER BY id;\n"
            "INSERT INTO recreate_test_new SELECT * FROM recreate_test;\n"
            "RENAME TABLE recreate_test TO recreate_test_old, recreate_test_new TO recreate_test;\n"
            "DROP TABLE recreate_test_old;",
            "DROP TABLE IF EXISTS recreate_test_new;",
        )

        stop_event = threading.Event()
        failures: list[str] = []
        successes = 0

        def reader():
            nonlocal successes
            while not stop_event.is_set():
                client = _ch_client(player.database_url)
                try:
                    client.query("SELECT COUNT() FROM recreate_test")
                    successes += 1
                except Exception as exc:  # noqa: BLE001
                    failures.append(str(exc))
                finally:
                    client.close()
                time.sleep(0.03)

        worker = threading.Thread(target=reader)
        worker.start()
        time.sleep(0.2)

        result = player.migrate()
        stop_event.set()
        worker.join(timeout=10)

        assert result.returncode == 0, result.output
        # The recreation pattern intentionally renames the live table away, so
        # some failures are expected and prove we observed the downtime window.
        assert failures, "Expected at least one failure while the table was renamed"
        assert successes > 0, "No successful reads occurred before/after the recreation"

        snapshot = DriftChecker().capture(player.database_url)
        assert dict(snapshot.table_options["recreate_test"])["engine"] == "ReplacingMergeTree"
    finally:
        provider.stop()
