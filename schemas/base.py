from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReferenceSchema:
    name: str
    models_py: Path
    expected_tables: tuple[str, ...]
    expected_indexes: tuple[str, ...]
    backend: str

    def source(self) -> str:
        return self.models_py.read_text(encoding="utf-8")
