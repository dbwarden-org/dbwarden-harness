from pathlib import Path

from infrastructure.providers import SQLiteProvider


def test_sqlite_provider_has_a_reproducible_lifecycle(tmp_path: Path):
    provider = SQLiteProvider(tmp_path / "harness.db")
    url = provider.start()
    assert url.startswith("sqlite:///")
    assert provider.version() == "sqlite"
    provider.stop()


def test_sqlite_provider_reset_removes_database(tmp_path: Path):
    provider = SQLiteProvider(tmp_path / "harness.db")
    provider.start()
    provider.path.touch()
    provider.reset()
    assert not provider.path.exists()
