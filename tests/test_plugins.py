from pathlib import Path

from harness.cli import CommandResult
from harness.plugins import PLUGIN_VERSION_MATRIX, REQUIRED_PLUGINS, PluginInstaller


def test_required_plugin_matrix_matches_public_install_commands(tmp_path: Path):
    installer = PluginInstaller(tmp_path)
    commands = [installer.build_add_command(plugin) for plugin in REQUIRED_PLUGINS]

    assert len(commands) == len(set(commands))
    assert all(command[:2] == ("plugin", "add") for command in commands)
    assert set(PLUGIN_VERSION_MATRIX) == set(REQUIRED_PLUGINS)


def test_plugin_discovery_requires_every_requested_distribution(tmp_path: Path):
    result = CommandResult(
        ("dbwarden", "plugin", "list"),
        0,
        "dbwarden-pgsql-types\ndbwarden-pgsql-rbac\n",
        "",
    )

    PluginInstaller.assert_discovered(result, REQUIRED_PLUGINS[:2])
