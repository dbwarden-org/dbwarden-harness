from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Self


class DatabaseProvider(ABC):
    """Lifecycle contract for a real database used by integration tests."""

    @abstractmethod
    def start(self) -> str:
        """Start the provider and return its connection URL."""

    @abstractmethod
    def stop(self) -> None:
        """Stop and dispose of the provider."""

    @abstractmethod
    def reset(self) -> None:
        """Clear user objects while retaining the running provider."""

    @abstractmethod
    def version(self) -> str:
        """Return the running database version."""

    def diagnostics(self) -> dict[str, Any]:
        """Return safe provider metadata suitable for failure artifacts."""
        return {"version": self.version()}

    def logs(self) -> str:
        """Return provider logs when the implementation can collect them."""
        return ""

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()
