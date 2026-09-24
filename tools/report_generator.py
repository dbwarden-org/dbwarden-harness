from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_junit_report(path: Path) -> dict[str, Any]:
    """Load pytest's portable JUnit XML through the standard library."""
    import xml.etree.ElementTree as ET

    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else root.findall(".//testsuite")
    leaves = [suite for suite in suites if suite.find("testsuite") is None]
    return {
        **{key: int(root.attrib[key]) if key in root.attrib else sum(int(suite.attrib.get(key, 0)) for suite in leaves)
           for key in ("tests", "failures", "errors", "skipped")},
        "suites": [
            {
                "name": suite.attrib.get("name", ""),
                "tests": int(suite.attrib.get("tests", 0)),
                "failures": int(suite.attrib.get("failures", 0)),
            }
            for suite in leaves
        ],
    }


def write_markdown_report(report: dict[str, Any], destination: Path) -> None:
    lines = ["# dbwarden Harness Report", "", f"- Tests: {report['tests']}", f"- Failures: {report['failures']}", f"- Errors: {report['errors']}", f"- Skipped: {report['skipped']}", "", "## Suites", ""]
    lines.extend(f"- `{suite['name']}`: {suite['tests']} tests, {suite['failures']} failures" for suite in report["suites"])
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_json_report(report: dict[str, Any], destination: Path) -> None:
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
