from pathlib import Path

from harness.plugins import REQUIRED_PLUGINS, PluginInstaller


def test_required_plugin_matrix_is_unique_and_public():
    assert len(REQUIRED_PLUGINS) == len(set(REQUIRED_PLUGINS))
    for distribution in REQUIRED_PLUGINS:
        command = PluginInstaller(Path("/tmp")).build_add_command(distribution)
        assert command[:2] == ("plugin", "add")
        assert command[2] == distribution


def test_plugin_install_command_pins_requested_version():
    command = PluginInstaller(Path("/tmp")).build_add_command("example-plugin", version="1.2.3")

    assert command == ("plugin", "add", "example-plugin==1.2.3")
