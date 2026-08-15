import os

import pytest

from harness.matrix import provider_versions
from infrastructure.providers import (
    ClickHouseProvider,
    MariaDBProvider,
    MySQLProvider,
    PostgresProvider,
)


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
