import pytest

from harness.cli import CommandResult


def test_command_result_requires_expected_failure_details():
    result = CommandResult(("dbwarden", "rollback"), 2, "", "configuration is missing")

    assert result.require_failure("configuration") is result
    assert "configuration" in result.output


def test_command_result_rejects_success_as_failure():
    result = CommandResult(("dbwarden", "status"), 0, "ok", "")

    with pytest.raises(AssertionError, match="Expected command to fail"):
        result.require_failure()
