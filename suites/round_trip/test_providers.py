import os

import pytest

from harness.matrix import provider_versions
from infrastructure.providers import (
    ClickHouseProvider,
    MariaDBProvider,
    MySQLProvider,
    PostgresProvider,
)
from tools.drift_checker import DriftChecker
from tools.migration_player import MigrationPlayer


def _selected_matrix_cases() -> tuple[tuple[str, str], ...]:
    backend = os.getenv("DBWARDEN_HARNESS_BACKEND")
    versions = os.getenv("DBWARDEN_HARNESS_VERSIONS")
    cases = tuple(provider_versions())
    if backend:
        cases = tuple(case for case in cases if case[0] == backend)
    if versions:
        allowed = set(versions.split(","))
        cases = tuple(case for case in cases if case[1] in allowed)
    return cases


@pytest.mark.integration
@pytest.mark.parametrize(
    "provider_type",
    [PostgresProvider, MySQLProvider, MariaDBProvider, ClickHouseProvider],
)
def test_real_provider_starts_and_resets(provider_type):
    with provider_type() as provider:
        url = provider.url()
        assert url
        assert provider.version()
        provider.reset()


@pytest.mark.integration
@pytest.mark.parametrize("backend,version", _selected_matrix_cases())
def test_declared_provider_matrix_starts_and_resets(backend: str, version: str):
    from infrastructure.providers import provider_for

    with provider_for(backend, version) as provider:
        url = provider.url()
        assert url
        assert provider.version() == version
        provider.reset()


@pytest.mark.integration
@pytest.mark.parametrize("backend,version", (("postgres", "17"), ("mysql", "8.4"), ("mariadb", "11.4"), ("clickhouse", "26.6")))
def test_provider_reset_removes_database_objects(backend: str, version: str, tmp_path):
    from infrastructure.providers import provider_for

    provider = provider_for(backend, version)
    try:
        player = MigrationPlayer(provider.start(), tmp_path)
        player.init_and_configure(database_type="postgresql" if backend == "postgres" else backend)
        migration_dir = tmp_path / "migrations" / "primary"
        migration_dir.mkdir(parents=True, exist_ok=True)
        statement = (
            "CREATE TABLE reset_probe (id Int64) ENGINE = MergeTree ORDER BY id;"
            if backend == "clickhouse"
            else "CREATE TABLE reset_probe (id INTEGER PRIMARY KEY);"
        )
        (migration_dir / "primary__0001_reset.sql").write_text(
            f"-- upgrade\n{statement}\n-- rollback\nDROP TABLE reset_probe;\n",
            encoding="utf-8",
        )
        player.migrate()
        assert "reset_probe" in DriftChecker().capture(player.database_url).tables

        provider.reset()

        assert "reset_probe" not in DriftChecker().capture(player.database_url).tables
    finally:
        provider.stop()
