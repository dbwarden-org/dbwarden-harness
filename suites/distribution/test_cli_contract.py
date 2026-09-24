from pathlib import Path

from harness.cli import DbwardenCli


def test_public_cli_help_has_core_commands(tmp_path: Path):
    result = DbwardenCli(tmp_path).run("--help")
    for command in (
        "init",
        "make-migrations",
        "migrate",
        "status",
        "rollback",
        "downgrade",
        "diff",
        "export-models",
        "generate-models",
        "check-impact",
        "merge",
        "rebase",
        "reconcile",
        "lock-status",
        "unlock",
    ):
        assert command in result.stdout


def test_public_cli_reports_a_version(tmp_path: Path):
    result = DbwardenCli(tmp_path).run("version")

    assert result.stdout.strip()
    assert result.plain_output.strip().count(".") == 2
