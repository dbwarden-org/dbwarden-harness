from __future__ import annotations

import os
from pathlib import Path

import pytest

from tools.case_runner import CaseRunner, clickhouse_urls, sqlite_urls
from tools.round_trip_driver import RoundTripDriver

CLICKHOUSE_VERSION = os.getenv("DBWARDEN_HARNESS_CLICKHOUSE_VERSION", "26.6")


@pytest.fixture(scope="session")
def clickhouse_endpoint() -> tuple[str, str]:
    """(clickhouse_url_authority, http_endpoint) for the generative matrices.

    Set ``DBWARDEN_HARNESS_CLICKHOUSE_URL`` to reuse an already-running server
    (much faster when iterating on a matrix locally); otherwise a disposable
    container is started for the whole session, because the matrices create one
    database per case rather than one container per case.
    """
    external = os.getenv("DBWARDEN_HARNESS_CLICKHOUSE_URL")
    if external:
        authority = external.split("://", 1)[-1].rsplit("/", 1)[0]
        host_port = authority.rsplit("@", 1)[-1]
        yield authority, f"http://{host_port}/"
        return

    # Imported lazily so that reusing an external server does not require
    # testcontainers to be installed.
    from infrastructure.providers import provider_for

    provider = provider_for("clickhouse", CLICKHOUSE_VERSION)
    provider.start()
    try:
        host, port = provider.host_port()
        yield f"clickhouse:clickhouse@{host}:{port}", f"http://clickhouse:clickhouse@{host}:{port}/"
    finally:
        provider.stop()


@pytest.fixture
def clickhouse_runner(tmp_path: Path, clickhouse_endpoint) -> CaseRunner:
    authority, http = clickhouse_endpoint
    return CaseRunner(
        tmp_path,
        url_for=clickhouse_urls(f"clickhouse://{authority}/"),
        clickhouse_http=http,
    )


@pytest.fixture
def clickhouse_round_trip(tmp_path: Path, clickhouse_runner) -> RoundTripDriver:
    def prepare(database: str) -> None:
        clickhouse_runner.clickhouse_query(f"DROP DATABASE IF EXISTS {database}")
        clickhouse_runner.clickhouse_query(f"CREATE DATABASE {database}")

    return RoundTripDriver(
        tmp_path,
        url_for=clickhouse_runner.url_for,
        backend="clickhouse",
        prepare_database=prepare,
    )


@pytest.fixture
def sqlite_runner(tmp_path: Path) -> CaseRunner:
    return CaseRunner(tmp_path, url_for=sqlite_urls)
