from pathlib import Path

import pytest

from harness.provenance import assert_installed_distribution, collect_provenance, file_sha256


def test_file_sha256_is_stable(tmp_path: Path):
    path = tmp_path / "lock"
    path.write_bytes(b"dbwarden")

    assert file_sha256(path) == file_sha256(path)
    assert file_sha256(tmp_path / "missing") is None


def test_collect_provenance_records_runtime_and_distribution():
    report = collect_provenance(distributions=("dbwarden",))

    assert report["python"]
    assert "dbwarden" in report["distributions"]


def test_source_checkout_resolution_is_rejected(tmp_path: Path):
    report = {"distributions": {"dbwarden": {"installed": True, "location": str(tmp_path)}}}

    with pytest.raises(AssertionError, match="source checkout"):
        assert_installed_distribution(report, checkout=tmp_path)
