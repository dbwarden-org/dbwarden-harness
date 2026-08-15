from __future__ import annotations

from dataclasses import dataclass
from importlib import metadata


@dataclass(frozen=True)
class DistributionReport:
    name: str
    version: str
    files: tuple[str, ...]
    entry_points: tuple[tuple[str, str, str], ...] = ()
    location: str = ""


def inspect_distribution(name: str = "dbwarden") -> DistributionReport:
    distribution = metadata.distribution(name)
    files = tuple(sorted(str(path) for path in (distribution.files or ())))
    entry_points = tuple(
        sorted((entry_point.group, entry_point.name, entry_point.value) for entry_point in distribution.entry_points)
    )
    location = str(distribution.locate_file(""))
    return DistributionReport(name, distribution.version, files, entry_points, location)


def inspect_distributions(names: tuple[str, ...]) -> tuple[DistributionReport, ...]:
    return tuple(inspect_distribution(name) for name in names)


def assert_wheel_is_clean(report: DistributionReport) -> None:
    leaked = [
        path
        for path in report.files
        if any(
            part in {"tests", ".git", ".env"} or path.endswith("dbwarden.py")
            for part in path.split("/")
        )
    ]
    if leaked:
        raise AssertionError(f"Development files leaked into {report.name}: {leaked}")


def assert_console_entry_point(report: DistributionReport) -> None:
    if not any(group == "console_scripts" and name == "dbwarden" for group, name, _ in report.entry_points):
        raise AssertionError(f"{report.name} does not expose the dbwarden console entry point")
