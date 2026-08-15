import pytest

from harness.distribution import (
    DistributionReport,
    assert_console_entry_point,
    assert_wheel_is_clean,
    inspect_distribution,
)
from harness.provenance import assert_installed_distribution, collect_provenance


def test_installed_dbwarden_distribution_is_inspectable():
    report = inspect_distribution()
    assert report.version
    assert "dbwarden/__init__.py" in report.files
    assert "site-packages" in report.location
    assert_wheel_is_clean(report)
    assert_console_entry_point(report)


def test_wheel_cleanliness_rejects_nested_development_files():
    report = DistributionReport("dbwarden", "0.0", ("dbwarden/__init__.py", "pkg/tests/test_smoke.py"))

    with pytest.raises(AssertionError, match="Development files"):
        assert_wheel_is_clean(report)


def test_installed_distribution_is_not_resolved_from_this_checkout():
    report = collect_provenance()
    assert_installed_distribution(report, checkout=__file__.rsplit("/tests/", 1)[0])
