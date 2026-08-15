import os
import sqlite3
import time
from contextlib import closing
from pathlib import Path

import pytest

from tools.drift_checker import DriftChecker
from tools.migration_player import MigrationPlayer
from tools.snapshot_manager import SnapshotManager


def _require_scale_suite() -> None:
    if os.getenv("DBWARDEN_HARNESS_RUN_SCALE") != "1":
        pytest.skip("set DBWARDEN_HARNESS_RUN_SCALE=1 to run scale benchmarks")


def test_200_table_migration_generation_scale(tmp_path: Path):
    _require_scale_suite()
    source = [
        "from sqlalchemy import Column, Integer",
        "from sqlalchemy.orm import declarative_base",
        "Base = declarative_base()",
        "",
    ]
    for number in range(200):
        source.extend(
            [
                f"class Table{number:03d}(Base):",
                f'    __tablename__ = "scale_{number:03d}"',
                "    id = Column(Integer, primary_key=True, autoincrement=False)",
                "",
            ]
        )
    player = MigrationPlayer(f"sqlite:///{tmp_path / 'scale.db'}", tmp_path)
    player.write_model_source("", filename="app/__init__.py")
    player.write_model_source("\n".join(source), filename="app/models.py")
    player.init_and_configure(model_paths=("app",))

    started = time.perf_counter()
    result = player.make_migrations("200 table scale")
    elapsed = time.perf_counter() - started

    assert result.returncode == 0
    assert elapsed > 0
    assert len(tuple((tmp_path / "migrations").rglob("*.sql"))) == 1


def test_1000_index_schema_snapshot_scale(tmp_path: Path):
    _require_scale_suite()
    database = tmp_path / "indexes.db"
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("CREATE TABLE indexed (id INTEGER PRIMARY KEY, value TEXT)")
        for number in range(1000):
            connection.execute(f"CREATE INDEX ix_indexed_{number:04d} ON indexed(value)")

    started = time.perf_counter()
    snapshot = DriftChecker().capture(f"sqlite:///{database}")
    elapsed = time.perf_counter() - started

    assert len(snapshot.indexes["indexed"]) == 1000
    assert elapsed > 0


def test_500_table_reverse_engineering_scale(tmp_path: Path):
    _require_scale_suite()
    database = tmp_path / "reverse.db"
    with closing(sqlite3.connect(database)) as connection:
        for number in range(500):
            connection.execute(
                f"CREATE TABLE reverse_{number:03d} (id INTEGER PRIMARY KEY, value TEXT)"
            )
    player = MigrationPlayer(f"sqlite:///{database}", tmp_path)
    player.init_and_configure()

    result = player.generate_models("--output", "generated", "--single-file")

    assert result.returncode == 0
    generated = (tmp_path / "generated" / "models.py").read_text(encoding="utf-8")
    assert generated.count("__tablename__") >= 500


def test_large_snapshot_serialization_scale(tmp_path: Path):
    _require_scale_suite()
    path = tmp_path / "large.sql"
    path.write_text(f"CREATE TABLE scale_{0:04d} (id INTEGER);\n" * 10000, encoding="utf-8")

    snapshot = SnapshotManager().capture(path)

    assert len(snapshot.content) > 100_000
