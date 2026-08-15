from __future__ import annotations

from pathlib import Path

from infrastructure.providers.base import DatabaseProvider


class SQLiteProvider(DatabaseProvider):
    """File-backed provider for dev-mode and distribution smoke tests."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def start(self) -> str:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{self.path}"

    def stop(self) -> None:
        return None

    def reset(self) -> None:
        if self.path.exists():
            self.path.unlink()

    def version(self) -> str:
        return "sqlite"
