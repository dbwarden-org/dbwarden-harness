import pytest

from tools.report_generator import load_junit_report


@pytest.mark.parametrize("wrapper", [False, True])
def test_junit_counts_include_pytest_testsuites_wrapper(tmp_path, wrapper):
    suite = '<testsuite name="pytest" tests="7" failures="2" errors="1" skipped="3" />'
    path = tmp_path / "results.xml"
    path.write_text(f"<testsuites>{suite}</testsuites>" if wrapper else suite, encoding="utf-8")
    report = load_junit_report(path)
    assert {key: report[key] for key in ("tests", "failures", "errors", "skipped")} == {"tests": 7, "failures": 2, "errors": 1, "skipped": 3}
    assert report["suites"] == [{"name": "pytest", "tests": 7, "failures": 2}]
