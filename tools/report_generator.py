from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_junit_report(path: Path) -> dict[str, Any]:
    """Load pytest's portable JUnit XML through the standard library."""
    import xml.etree.ElementTree as ET

    root = ET.parse(path).getroot()
    return {
        "tests": int(root.attrib.get("tests", 0)),
        "failures": int(root.attrib.get("failures", 0)),
        "errors": int(root.attrib.get("errors", 0)),
        "skipped": int(root.attrib.get("skipped", 0)),
        "suites": [
            {
                "name": suite.attrib.get("name", ""),
                "tests": int(suite.attrib.get("tests", 0)),
                "failures": int(suite.attrib.get("failures", 0)),
            }
            for suite in root.findall(".//testsuite")
        ],
    }


def write_markdown_report(report: dict[str, Any], destination: Path) -> None:
    lines = ["# dbwarden Harness Report", "", f"- Tests: {report['tests']}", f"- Failures: {report['failures']}", f"- Errors: {report['errors']}", f"- Skipped: {report['skipped']}", "", "## Suites", ""]
    lines.extend(f"- `{suite['name']}`: {suite['tests']} tests, {suite['failures']} failures" for suite in report["suites"])
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_json_report(report: dict[str, Any], destination: Path) -> None:
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
