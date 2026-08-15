import pytest

from harness.distribution import assert_wheel_is_clean, inspect_distributions
from harness.plugins import REQUIRED_PLUGINS, PluginInstaller


@pytest.mark.integration
def test_plugin_installation_uses_public_cli(tmp_path):
    installer = PluginInstaller(tmp_path)
    results = installer.add_required()
    assert all(result.returncode == 0 for result in results)
    installer.assert_discovered(installer.list())
    for report in inspect_distributions(REQUIRED_PLUGINS):
        assert report.version
        assert_wheel_is_clean(report)
