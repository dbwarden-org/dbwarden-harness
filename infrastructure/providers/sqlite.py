from __future__ import annotations

import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

from infrastructure.providers.base import DatabaseProvider


class SQLiteProvider(DatabaseProvider):
    """File-backed provider for the SQLite backend.

    SQLite is a first-class dbwarden backend, so it answers the same provider
    contract as the container backends: ``start``/``stop``/``reset``/``url``/
    ``version``. Passing no path makes the provider own a temporary directory
    that it removes on ``stop``, which is what ``provider_for`` needs to build a
    SQLite provider from a backend name alone.
    """

    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self._owns_directory = path is None
        self._directory: Path | None = None

    def start(self) -> str:
        if self.path is None:
            self._directory = Path(tempfile.mkdtemp(prefix="dbwarden-harness-sqlite-"))
            self.path = self._directory / "harness.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        return self.url()

    def url(self) -> str:
        if self.path is None:
            raise RuntimeError("SQLiteProvider.start() must run before url()")
        return f"sqlite:///{self.path}"

    def stop(self) -> None:
        if self._owns_directory and self._directory is not None:
            shutil.rmtree(self._directory, ignore_errors=True)
            self._directory = None
            self.path = None

    def reset(self) -> None:
        if self.path is not None and self.path.exists():
            self.path.unlink()

    def version(self) -> str:
        return sqlite3.sqlite_version

    def diagnostics(self) -> dict[str, Any]:
        return {
            "version": self.version(),
            "path": str(self.path) if self.path else None,
        }
