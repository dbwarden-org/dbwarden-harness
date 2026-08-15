from pathlib import Path

from tools.drift_checker import DriftChecker, SchemaSnapshot
from tools.report_generator import write_json_report, write_markdown_report
from tools.snapshot_manager import SnapshotManager


def test_snapshot_manager_detects_and_approves_sql_changes(tmp_path: Path):
    manager = SnapshotManager()
    first = tmp_path / "first.sql"
    second = tmp_path / "second.sql"
    first.write_text("CREATE TABLE users (id INT);\n", encoding="utf-8")
    second.write_text("CREATE TABLE users (id BIGINT);\n", encoding="utf-8")

    diff = manager.compare(manager.capture(second), manager.capture(first))
    assert diff.changed
    assert "-CREATE TABLE users (id INT);" in diff.unified_text
    manager.approve(diff, tmp_path / "approved" / "users.sql")
    assert (tmp_path / "approved/users.sql").read_text(encoding="utf-8") == second.read_text(encoding="utf-8")


def test_drift_checker_compares_structural_snapshots():
    checker = DriftChecker()
    expected = SchemaSnapshot(("users",), {"users": ("id",)}, {"users": ()})
    actual = SchemaSnapshot(("users",), {"users": ("id", "email")}, {"users": ()})

    assert len(checker.diff(expected, actual)) == 1


def test_drift_checker_compares_backend_table_options():
    checker = DriftChecker()
    expected = SchemaSnapshot(
        ("events",),
        {"events": ("id",)},
        {"events": ()},
        table_options={"events": (("engine", "MergeTree"),)},
    )
    actual = SchemaSnapshot(
        ("events",),
        {"events": ("id",)},
        {"events": ()},
        table_options={"events": (("engine", "ReplacingMergeTree"),)},
    )

    drift = checker.diff(expected, actual)

    assert [(item.kind, item.object_name) for item in drift] == [("table_options", "events")]


def test_report_writers_emit_machine_and_human_readable_reports(tmp_path: Path):
    report = {"tests": 2, "failures": 0, "errors": 0, "skipped": 1, "suites": []}
    write_json_report(report, tmp_path / "report.json")
    write_markdown_report(report, tmp_path / "report.md")
    assert '"tests": 2' in (tmp_path / "report.json").read_text(encoding="utf-8")
    assert "# dbwarden Harness Report" in (tmp_path / "report.md").read_text(encoding="utf-8")
