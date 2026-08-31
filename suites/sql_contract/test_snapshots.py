from pathlib import Path

import pytest

from harness.distribution import inspect_distribution
from harness.reference import MINIMAL_SQLITE_MODELS
from tools.migration_player import MigrationPlayer
from tools.snapshot_manager import SnapshotManager

SNAPSHOTS_ROOT = Path(__file__).parents[2] / "snapshots"


def test_snapshot_manifest_is_intact():
    """The baselines themselves must not drift, whichever release is installed."""
    SnapshotManager().verify_manifest(SNAPSHOTS_ROOT)


def test_sql_contract_snapshot_is_byte_stable(tmp_path: Path):
    manager = SnapshotManager()
    version = inspect_distribution("dbwarden").version
    baseline = manager.baseline_for(
        SNAPSHOTS_ROOT, version=version, backend="sqlite", name="minimal.sql",
    )
    if baseline is None:
        # Comparing against another release's baseline would report every
        # intentional backend fix as a regression. A new release needs its
        # contract approved deliberately, not inherited.
        pytest.skip(
            f"No approved SQL baseline for dbwarden {version}. To approve one: "
            f"generate the minimal SQLite migration, save it as "
            f"snapshots/v{version}/sqlite/minimal.sql, and rewrite the manifest "
            f"with SnapshotManager().write_manifest(snapshots)."
        )

    player = MigrationPlayer(f"sqlite:///{tmp_path / 'app.db'}", tmp_path)
    player.write_model_source("", filename="app/__init__.py")
    player.write_model_source(MINIMAL_SQLITE_MODELS, filename="app/models.py")
    player.init_and_configure(model_paths=("app",))
    player.make_migrations("snapshot")
    current = next((tmp_path / "migrations").rglob("*.sql"))

    diff = manager.compare(manager.capture(current), manager.capture(baseline))
    manager.assert_unchanged(diff)
