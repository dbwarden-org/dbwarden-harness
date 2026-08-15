from pathlib import Path

import pytest

from harness.reference import MINIMAL_SQLITE_MODELS
from tools.migration_player import MigrationPlayer
from tools.offline_integrity import verify_state_manifest, write_state_manifest


def test_sqlite_offline_generation_uses_exported_model_state(tmp_path: Path):
    player = MigrationPlayer(f"sqlite:///{tmp_path / 'app.db'}", tmp_path)
    player.write_model_source("", filename="app/__init__.py")
    player.write_model_source(MINIMAL_SQLITE_MODELS, filename="app/models.py")
    player.init_and_configure(model_paths=("app",))
    player.export_models()

    result = player.make_migrations("offline state", "--offline")
    assert result.returncode == 0
    assert (tmp_path / ".dbwarden").is_dir()
    assert "offline" in result.stdout.lower() or "no changes" in result.stdout.lower()


def test_offline_model_state_checksum_detects_tampering(tmp_path: Path):
    player = MigrationPlayer(f"sqlite:///{tmp_path / 'app.db'}", tmp_path)
    player.write_model_source("", filename="app/__init__.py")
    player.write_model_source(MINIMAL_SQLITE_MODELS, filename="app/models.py")
    player.init_and_configure(model_paths=("app",))
    player.export_models()

    manifest = write_state_manifest(tmp_path)
    verify_state_manifest(tmp_path, manifest)
    state = next(
        path
        for path in (tmp_path / ".dbwarden").glob("model_state*.json")
        if not path.name.endswith(".SHA256SUMS.json")
    )
    state.write_text(state.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    with pytest.raises(AssertionError, match="checksum mismatch"):
        verify_state_manifest(tmp_path, manifest)


def test_deleted_model_state_is_recovered_from_applied_migrations(tmp_path: Path):
    player = MigrationPlayer(f"sqlite:///{tmp_path / 'app.db'}", tmp_path)
    player.write_model_source("", filename="app/__init__.py")
    player.write_model_source(MINIMAL_SQLITE_MODELS, filename="app/models.py")
    player.init_and_configure(model_paths=("app",))
    player.make_migrations("recovery baseline")
    player.migrate()
    player.export_models()

    state = tmp_path / ".dbwarden" / "model_state.primary.json"
    state.unlink()
    result = player.cli.run("recover-model-state", check=False)

    assert result.returncode == 0
    assert "recovered" in result.output.lower()
    assert state.exists()


def test_offline_generation_reports_absent_state(tmp_path: Path):
    player = MigrationPlayer(f"sqlite:///{tmp_path / 'app.db'}", tmp_path)
    player.write_model_source("", filename="app/__init__.py")
    player.write_model_source(MINIMAL_SQLITE_MODELS, filename="app/models.py")
    player.init_and_configure(model_paths=("app",))
    player.export_models()
    for state in (tmp_path / ".dbwarden").glob("model_state*.json"):
        state.unlink()

    result = player.cli.run("make-migrations", "offline", "--offline", check=False)

    assert "model_state.primary.json not found" in result.output
    assert not tuple((tmp_path / "migrations").rglob("*.sql"))
