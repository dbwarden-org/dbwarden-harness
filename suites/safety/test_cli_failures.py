from pathlib import Path

import pytest

from harness.cli import DbwardenCli
from harness.reference import MINIMAL_SQLITE_MODELS
from tools.migration_player import MigrationPlayer


def test_invalid_cli_command_is_reported_without_synthetic_success(tmp_path: Path):
    result = DbwardenCli(tmp_path).run("command-that-does-not-exist", check=False)
    assert result.returncode != 0
    assert result.stderr


@pytest.mark.parametrize(
    "command",
    [("rollback", "--count", "1"), ("downgrade", "--to", "0001"), ("check",)],
)
def test_stateful_commands_fail_without_a_consumer_configuration(tmp_path: Path, command: tuple[str, ...]):
    result = DbwardenCli(tmp_path).run(*command, check=False)

    result.require_failure()


def test_safety_check_reports_non_destructive_info_changes(tmp_path: Path):
    player = MigrationPlayer(f"sqlite:///{tmp_path / 'app.db'}", tmp_path)
    player.write_model_source("", filename="app/__init__.py")
    player.write_model_source(MINIMAL_SQLITE_MODELS, filename="app/models.py")
    player.init_and_configure(model_paths=("app",))
    player.make_migrations("initial schema")

    result = player.cli.run("check", check=False)

    assert result.returncode == 0
    assert "info" in result.output.lower()
    assert "create_table" in result.output.lower()


def test_warning_level_destructive_migration_requires_force(tmp_path: Path):
    player = MigrationPlayer(f"sqlite:///{tmp_path / 'app.db'}", tmp_path)
    player.write_model_source("", filename="app/__init__.py")
    player.write_model_source(MINIMAL_SQLITE_MODELS, filename="app/models.py")
    player.init_and_configure(model_paths=("app",))
    player.make_migrations("initial schema")
    player.migrate()
    migration_dir = tmp_path / "migrations" / "primary"
    (migration_dir / "primary__0002_drop_users.sql").write_text(
        "-- upgrade\nDROP TABLE users;\n"
        "-- rollback\nCREATE TABLE users (id INTEGER PRIMARY KEY);\n",
        encoding="utf-8",
    )

    blocked = player.cli.run("check", check=False)
    forced = player.cli.run("check", "--force", check=False)

    assert blocked.returncode != 0
    assert "require --force" in blocked.output.lower()
    assert forced.returncode == 0
