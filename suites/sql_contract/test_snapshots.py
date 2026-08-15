from pathlib import Path

from harness.reference import MINIMAL_SQLITE_MODELS
from tools.migration_player import MigrationPlayer
from tools.snapshot_manager import SnapshotManager


def test_sql_contract_snapshot_is_byte_stable(tmp_path: Path):
    manager = SnapshotManager()
    snapshots_root = Path(__file__).parents[2] / "snapshots"
    manager.verify_manifest(snapshots_root)
    baseline = snapshots_root / "v0.16.5" / "sqlite" / "minimal.sql"
    player = MigrationPlayer(f"sqlite:///{tmp_path / 'app.db'}", tmp_path)
    player.write_model_source("", filename="app/__init__.py")
    player.write_model_source(MINIMAL_SQLITE_MODELS, filename="app/models.py")
    player.init_and_configure(model_paths=("app",))
    player.make_migrations("snapshot")
    current = next((tmp_path / "migrations").rglob("*.sql"))

    diff = manager.compare(manager.capture(current), manager.capture(baseline))
    manager.assert_unchanged(diff)
