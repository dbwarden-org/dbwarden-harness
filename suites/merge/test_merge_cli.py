"""Black-box CLI tests for the merge, rebase, reconcile, lock-status, and
unlock commands added in v0.18.0/v0.19.0.

These tests exercise the CLI surface (error modes, flag parsing, help text)
without requiring a live database.  Integration tests for the full merge
workflow belong in suites/adversarial/ or suites/round_trip/.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from harness.cli import DbwardenCli
from harness.reference import MINIMAL_SQLITE_MODELS
from tools.migration_player import MigrationPlayer

# ---------------------------------------------------------------------------
# CLI presence and help text
# ---------------------------------------------------------------------------


def test_merge_command_appears_in_help(tmp_path: Path):
    result = DbwardenCli(tmp_path).run("--help")
    assert "merge" in result.stdout
    assert "divergent" in result.stdout.lower() or "branch" in result.stdout.lower()


def test_rebase_command_appears_in_help(tmp_path: Path):
    result = DbwardenCli(tmp_path).run("--help")
    assert "rebase" in result.stdout
    assert "disposable" in result.stdout.lower() or "recover" in result.stdout.lower()


def test_reconcile_command_appears_in_help(tmp_path: Path):
    result = DbwardenCli(tmp_path).run("--help")
    assert "reconcile" in result.stdout
    assert "persistent" in result.stdout.lower() or "dirty" in result.stdout.lower()


def test_lock_status_command_appears_in_help(tmp_path: Path):
    result = DbwardenCli(tmp_path).run("--help")
    assert "lock-status" in result.stdout


def test_unlock_command_appears_in_help(tmp_path: Path):
    result = DbwardenCli(tmp_path).run("--help")
    assert "unlock" in result.stdout


# ---------------------------------------------------------------------------
# Error modes: commands fail gracefully outside a dbwarden project
# ---------------------------------------------------------------------------


def test_merge_fails_without_project(tmp_path: Path):
    result = DbwardenCli(tmp_path).run("merge", check=False)
    assert result.returncode != 0


def test_rebase_fails_without_project(tmp_path: Path):
    result = DbwardenCli(tmp_path).run("rebase", check=False)
    assert result.returncode != 0


def test_lock_status_fails_without_project(tmp_path: Path):
    result = DbwardenCli(tmp_path).run("lock-status", check=False)
    assert result.returncode != 0


def test_unlock_fails_without_project(tmp_path: Path):
    result = DbwardenCli(tmp_path).run("unlock", check=False)
    assert result.returncode != 0


# ---------------------------------------------------------------------------
# Graceful handling: commands that detect "nothing to do" exit cleanly
# ---------------------------------------------------------------------------


def test_merge_handles_dirty_tree_without_git(tmp_path: Path):
    """merge exits 0 with a warning when the working tree is dirty (no git repo)."""
    player = MigrationPlayer(f"sqlite:///{tmp_path / 'app.db'}", tmp_path)
    player.write_model_source("", filename="app/__init__.py")
    player.write_model_source(MINIMAL_SQLITE_MODELS, filename="app/models.py")
    player.init_and_configure(model_paths=("app",))

    result = player.cli.run("merge", check=False)
    assert result.returncode == 0
    output = result.output.lower()
    assert "clean" in output or "nothing" in output or "no divergent" in output


def test_rebase_handles_no_migrations_without_git(tmp_path: Path):
    """rebase exits 0 when no migrations have been applied."""
    player = MigrationPlayer(f"sqlite:///{tmp_path / 'app.db'}", tmp_path)
    player.write_model_source("", filename="app/__init__.py")
    player.write_model_source(MINIMAL_SQLITE_MODELS, filename="app/models.py")
    player.init_and_configure(model_paths=("app",))

    result = player.cli.run("rebase", check=False)
    assert result.returncode == 0
    output = result.output.lower()
    assert "converged" in output or "no migration" in output or "nothing" in output


# ---------------------------------------------------------------------------
# merge --help / rebase --help flag parsing
# ---------------------------------------------------------------------------


def test_merge_help_lists_flags(tmp_path: Path):
    result = DbwardenCli(tmp_path).run("merge", "--help")
    assert result.returncode == 0
    assert "--rename-column" in result.stdout
    assert "--rename-table" in result.stdout
    assert "--force" in result.stdout
    assert "--commit" in result.stdout
    assert "--json" in result.stdout


def test_rebase_help_lists_flags(tmp_path: Path):
    result = DbwardenCli(tmp_path).run("rebase", "--help")
    assert result.returncode == 0
    assert "--yes" in result.stdout
    assert "--force" in result.stdout
    assert "--check" in result.stdout


def test_reconcile_help_lists_flags(tmp_path: Path):
    result = DbwardenCli(tmp_path).run("reconcile", "--help")
    assert result.returncode == 0
    assert "--dry-run" in result.stdout
    assert "--rename-column" in result.stdout
    assert "environment" in result.stdout.lower()


def test_unlock_help_lists_flags(tmp_path: Path):
    result = DbwardenCli(tmp_path).run("unlock", "--help")
    assert result.returncode == 0
    assert "--force" in result.stdout


# ---------------------------------------------------------------------------
# reconcile requires an environment argument
# ---------------------------------------------------------------------------


def test_reconcile_requires_environment_argument(tmp_path: Path):
    result = DbwardenCli(tmp_path).run("reconcile", check=False)
    assert result.returncode != 0


# ---------------------------------------------------------------------------
# status --all-environments flag
# ---------------------------------------------------------------------------


def test_status_all_environments_flag_present(tmp_path: Path):
    result = DbwardenCli(tmp_path).run("status", "--help")
    assert "--all-environments" in result.stdout


def test_status_all_environments_outside_project(tmp_path: Path):
    result = DbwardenCli(tmp_path).run("status", "--all-environments", check=False)
    assert result.returncode != 0


@pytest.mark.xfail(reason="dbwarden bug: 'info' not imported in _show_all_environments_status")
def test_status_all_environments_inside_project(tmp_path: Path):
    player = MigrationPlayer(f"sqlite:///{tmp_path / 'app.db'}", tmp_path)
    player.write_model_source("", filename="app/__init__.py")
    player.write_model_source(MINIMAL_SQLITE_MODELS, filename="app/models.py")
    player.init_and_configure(model_paths=("app",))

    result = player.cli.run("status", "--all-environments")
    assert result.returncode == 0
