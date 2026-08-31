import sqlite3
from pathlib import Path

from infrastructure.providers import SQLiteProvider, provider_for


def test_sqlite_provider_has_a_reproducible_lifecycle(tmp_path: Path):
    provider = SQLiteProvider(tmp_path / "harness.db")
    url = provider.start()
    assert url.startswith("sqlite:///")
    assert provider.version() == sqlite3.sqlite_version
    provider.stop()
    assert provider.path.parent.exists(), "a caller-owned directory must survive stop()"


def test_sqlite_provider_reset_removes_database(tmp_path: Path):
    provider = SQLiteProvider(tmp_path / "harness.db")
    provider.start()
    provider.path.touch()
    provider.reset()
    assert not provider.path.exists()


def test_sqlite_provider_without_a_path_owns_its_directory():
    """`provider_for` builds SQLite from a backend name, so the path is its own."""
    provider = SQLiteProvider()
    url = provider.start()
    owned = provider.path
    assert url == f"sqlite:///{owned}"
    provider.stop()
    assert not owned.parent.exists(), "the temporary directory outlived the provider"


def test_provider_for_builds_sqlite_without_a_version():
    provider = provider_for("sqlite", "local")
    try:
        assert provider.start().startswith("sqlite:///")
        assert provider.version()
    finally:
        provider.stop()
