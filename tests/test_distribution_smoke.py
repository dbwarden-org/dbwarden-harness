from pathlib import Path

from harness.cli import DbwardenCli


def test_installed_dbwarden_cli_reports_a_version(tmp_path: Path):
    result = DbwardenCli(tmp_path).run("version")
    assert result.stdout.strip()
    assert not result.stderr
