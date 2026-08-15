from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from harness.cli import DbwardenCli
from tools.migration_player import MigrationPlayer


@dataclass(frozen=True)
class ConvergenceBenchmarkResult:
    migration_count: int
    prepare_seconds: float
    migrate_seconds: float
    diff_seconds: float
    total_seconds: float

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2) + "\n"


def model_source(migration_count: int) -> str:
    lines = [
        "from sqlalchemy import Column, Integer",
        "from sqlalchemy.orm import declarative_base",
        "from dbwarden.databases import TableMeta",
        "",
        "Base = declarative_base()",
        "",
    ]
    for index in range(1, migration_count + 1):
        lines.extend(
            [
                f"class Table{index:04d}(Base):",
                f'    __tablename__ = "table_{index:04d}"',
                "    id = Column(Integer, primary_key=True)",
                "    class Meta(TableMeta):",
                f'        comment = "Benchmark table {index:04d}"',
                "",
            ]
        )
    return "\n".join(lines)


def create_history(work_dir: Path, migration_count: int) -> None:
    migration_dir = work_dir / "migrations" / "primary"
    migration_dir.mkdir(parents=True, exist_ok=True)
    for index in range(1, migration_count + 1):
        migration_id = f"{index:04d}"
        table = f"table_{index:04d}"
        (migration_dir / f"primary__{migration_id}_create_{table}.sql").write_text(
            f"-- upgrade\nCREATE TABLE {table} (id INTEGER PRIMARY KEY);\n"
            f"-- rollback\nDROP TABLE {table};\n",
            encoding="utf-8",
        )


def run_convergence_benchmark(
    work_dir: Path,
    *,
    migration_count: int = 500,
    executable: str = "dbwarden",
) -> ConvergenceBenchmarkResult:
    if migration_count <= 0:
        raise ValueError("migration_count must be positive")

    started = time.perf_counter()
    database_url = f"sqlite:///{work_dir / 'app.db'}"
    player = MigrationPlayer(database_url, work_dir)
    player.cli = DbwardenCli(work_dir, executable=executable)
    player.init()
    player.write_model_source("", filename="app/__init__.py")
    player.write_model_source(model_source(migration_count), filename="app/models.py")
    player.configure(model_paths=("app",))
    create_history(work_dir, migration_count)
    prepared = time.perf_counter()

    migrate_flags = ("--defer-snapshots",) if os.getenv("DBWARDEN_HARNESS_DEFER_SNAPSHOTS") == "1" else ()
    player.cli.run("migrate", *migrate_flags, timeout=900.0)
    migrated = time.perf_counter()
    player.cli.run("diff", timeout=900.0)
    checked = time.perf_counter()

    return ConvergenceBenchmarkResult(
        migration_count=migration_count,
        prepare_seconds=prepared - started,
        migrate_seconds=migrated - prepared,
        diff_seconds=checked - migrated,
        total_seconds=checked - started,
    )
