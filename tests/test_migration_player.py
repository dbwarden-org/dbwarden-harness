from pathlib import Path

from tools.migration_player import MigrationPlayer


def test_migration_player_initializes_a_project(tmp_path: Path):
    player = MigrationPlayer("sqlite:///unused.db", tmp_path)
    config_path = player.init_and_configure()

    assert config_path.exists()
    assert (tmp_path / "dbwarden.py").exists()
    assert (tmp_path / "migrations").is_dir()
    assert "sqlite:///unused.db" in config_path.read_text(encoding="utf-8")
