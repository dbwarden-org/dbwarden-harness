"""Black-box CLI tests for v2 migration locking features added in v0.18.0.

Tests config key acceptance (lock_namespace, clickhouse_lock_ttl),
lock-status / unlock CLI surface, and per-engine strategy dispatch.
These tests exercise the CLI surface using SQLite (no Docker required).
"""

from __future__ import annotations

from pathlib import Path

from harness.cli import DbwardenCli
from harness.reference import MINIMAL_SQLITE_MODELS
from tools.migration_player import MigrationPlayer


def _init_player(tmp_path: Path, **config_kwargs: object) -> MigrationPlayer:
    """Set up a minimal dbwarden project with optional config overrides."""
    player = MigrationPlayer(f"sqlite:///{tmp_path / 'app.db'}", tmp_path)
    player.write_model_source("", filename="app/__init__.py")
    player.write_model_source(MINIMAL_SQLITE_MODELS, filename="app/models.py")
    player.init_and_configure(model_paths=("app",), **config_kwargs)
    return player


# ---------------------------------------------------------------------------
# Config key acceptance: new v2 config keys in dbwarden.py
# ---------------------------------------------------------------------------


def test_lock_namespace_config_key_accepted(tmp_path: Path):
    player = _init_player(tmp_path, lock_namespace="my_ns")
    dbwarden_py = (tmp_path / "dbwarden.py").read_text()
    assert "lock_namespace='my_ns'" in dbwarden_py
    # dbwarden should not crash when loading this config
    result = player.cli.run("config")
    assert result.returncode == 0


def test_clickhouse_lock_ttl_config_key_accepted(tmp_path: Path):
    player = _init_player(tmp_path, clickhouse_lock_ttl=60)
    dbwarden_py = (tmp_path / "dbwarden.py").read_text()
    assert "clickhouse_lock_ttl=60" in dbwarden_py
    result = player.cli.run("config")
    assert result.returncode == 0


def test_ch_cluster_config_key_accepted(tmp_path: Path):
    player = _init_player(tmp_path, ch_cluster="my_cluster")
    dbwarden_py = (tmp_path / "dbwarden.py").read_text()
    assert "ch_cluster='my_cluster'" in dbwarden_py
    result = player.cli.run("config")
    assert result.returncode == 0


def test_ch_replicated_database_config_key_accepted(tmp_path: Path):
    player = _init_player(tmp_path, ch_replicated_database=True)
    dbwarden_py = (tmp_path / "dbwarden.py").read_text()
    assert "ch_replicated_database=True" in dbwarden_py
    result = player.cli.run("config")
    assert result.returncode == 0


def test_invalid_config_key_rejected(tmp_path: Path):
    """Unknown keyword arguments to database_config() raise an error."""
    player = _init_player(tmp_path, totally_fake_key="oops")
    result = player.cli.run("config", check=False)
    assert result.returncode != 0
    assert "unexpected keyword argument" in result.output.lower()


# ---------------------------------------------------------------------------
# lock-status / unlock CLI surface (require lock table via make+migrate)
# ---------------------------------------------------------------------------


def test_lock_status_outside_project(tmp_path: Path):
    result = DbwardenCli(tmp_path).run("lock-status", check=False)
    assert result.returncode != 0


def test_unlock_outside_project(tmp_path: Path):
    result = DbwardenCli(tmp_path).run("unlock", check=False)
    assert result.returncode != 0


def test_lock_status_reports_inactive_when_no_lock(tmp_path: Path):
    player = _init_player(tmp_path)
    player.make_migrations("initial")
    player.migrate()

    result = player.cli.run("lock-status")
    assert result.returncode == 0
    output = result.output.lower()
    assert "inactive" in output or "not locked" in output or "available" in output


def test_lock_status_json_output(tmp_path: Path):
    player = _init_player(tmp_path)
    player.make_migrations("initial")
    player.migrate()

    result = player.cli.run("--json", "lock-status")
    assert result.returncode == 0
    assert '"locked"' in result.stdout


def test_unlock_without_lock_succeeds(tmp_path: Path):
    player = _init_player(tmp_path)
    player.make_migrations("initial")
    player.migrate()

    result = player.cli.run("unlock", "--force")
    assert result.returncode == 0
