from pathlib import Path

from tools.snapshot_manager import SnapshotManager


def test_snapshot_capture_benchmark(benchmark, tmp_path: Path):
    path = tmp_path / "large.sql"
    path.write_text("CREATE TABLE users (id INTEGER);\n" * 200, encoding="utf-8")
    manager = SnapshotManager()
    result = benchmark(manager.capture, path)
    assert result.sha256
