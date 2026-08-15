from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass


@dataclass(frozen=True)
class VersionMatrix:
    python: tuple[str, ...] = ("3.12", "3.13")
    postgres: tuple[str, ...] = ("14", "15", "16", "17")
    clickhouse: tuple[str, ...] = ("24.3", "26.6")
    mysql: tuple[str, ...] = ("8.0", "8.4")
    mariadb: tuple[str, ...] = ("10.11", "11.4")


DEFAULT_MATRIX = VersionMatrix()


def provider_versions(matrix: VersionMatrix = DEFAULT_MATRIX) -> Iterator[tuple[str, str]]:
    for backend, versions in (
        ("postgres", matrix.postgres),
        ("clickhouse", matrix.clickhouse),
        ("mysql", matrix.mysql),
        ("mariadb", matrix.mariadb),
    ):
        for version in versions:
            yield backend, version
