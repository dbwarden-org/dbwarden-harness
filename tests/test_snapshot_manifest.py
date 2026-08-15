from pathlib import Path

import pytest

from tools.snapshot_manager import SnapshotManager


def test_snapshot_manifest_detects_tampering_and_unexpected_files(tmp_path: Path):
    snapshot = tmp_path / "sqlite" / "minimal.sql"
    snapshot.parent.mkdir()
    snapshot.write_text("CREATE TABLE users (id INTEGER);\n", encoding="utf-8")
    manager = SnapshotManager()
    manifest = manager.write_manifest(tmp_path)

    manager.verify_manifest(tmp_path, manifest)
    snapshot.write_text("CREATE TABLE users (id TEXT);\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="changed"):
        manager.verify_manifest(tmp_path, manifest)
