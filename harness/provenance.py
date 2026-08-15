from __future__ import annotations

import hashlib
import importlib.metadata
import platform
import sys
from pathlib import Path
from typing import Any

from harness.distribution import inspect_distribution


def file_sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_provenance(
    *,
    lockfile: Path | None = None,
    distributions: tuple[str, ...] = ("dbwarden",),
) -> dict[str, Any]:
    reports: dict[str, Any] = {}
    for name in distributions:
        try:
            report = inspect_distribution(name)
        except importlib.metadata.PackageNotFoundError:
            reports[name] = {"installed": False}
            continue
        reports[name] = {
            "installed": True,
            "version": report.version,
            "location": report.location,
            "entry_points": report.entry_points,
        }
    return {
        "python": sys.version,
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "distributions": reports,
        "lockfile": str(lockfile) if lockfile else None,
        "lockfile_sha256": file_sha256(lockfile) if lockfile else None,
    }


def assert_installed_distribution(report: dict[str, Any], *, checkout: Path | str | None = None) -> None:
    dbwarden = report.get("distributions", {}).get("dbwarden", {})
    if not dbwarden.get("installed"):
        raise AssertionError("dbwarden is not installed in the harness environment")
    if checkout is not None:
        location = Path(dbwarden.get("location", "")).resolve()
        checkout = Path(checkout).resolve()
        if location == checkout or location in checkout.parents:
            raise AssertionError(f"Harness resolved dbwarden from the source checkout: {location}")
