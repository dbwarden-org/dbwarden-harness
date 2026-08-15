from pathlib import Path

from harness.reference import MINIMAL_SQLITE_MODELS
from tools.migration_player import MigrationPlayer
from tools.snapshot_manager import SnapshotManager


def test_same_cli_input_produces_identical_migration_artifacts(tmp_path: Path):
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    manager = SnapshotManager()

    for work_dir in (first_dir, second_dir):
        work_dir.mkdir()
        player = MigrationPlayer(f"sqlite:///{work_dir / 'app.db'}", work_dir)
        player.write_model_source("", filename="app/__init__.py")
        player.write_model_source(MINIMAL_SQLITE_MODELS, filename="app/models.py")
        player.init_and_configure(model_paths=("app",))
        player.make_migrations("deterministic schema")

    first = next((first_dir / "migrations").rglob("*.sql"))
    second = next((second_dir / "migrations").rglob("*.sql"))
    assert manager.capture(first).sha256 == manager.capture(second).sha256
