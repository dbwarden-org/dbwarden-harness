from pathlib import Path

from harness.matrix import DEFAULT_MATRIX
from harness.plugins import PluginInstaller


def test_default_matrix_contains_spec_versions():
    assert DEFAULT_MATRIX.postgres == ("14", "15", "16", "17")
    assert DEFAULT_MATRIX.clickhouse == ("24.3", "26.6")


def test_plugin_installer_builds_pinned_public_cli_command(tmp_path: Path):
    installer = PluginInstaller(tmp_path)
    assert installer.build_add_command("dbwarden-pgsql-types", version="1.2.3") == (
        "plugin",
        "add",
        "dbwarden-pgsql-types==1.2.3",
    )
