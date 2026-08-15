from __future__ import annotations

from pathlib import Path

from schemas.base import ReferenceSchema


def discover_schemas(root: Path | None = None) -> tuple[ReferenceSchema, ...]:
    root = root or Path(__file__).parent
    schemas: list[ReferenceSchema] = []
    for directory in sorted(path for path in root.iterdir() if path.is_dir() and not path.name.startswith("__")):
        metadata_path = directory / "schema.json"
        if not metadata_path.exists():
            continue
        import json

        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        schemas.append(
            ReferenceSchema(
                name=metadata["name"],
                models_py=directory / metadata["models"],
                expected_tables=tuple(metadata.get("expected_tables", ())),
                expected_indexes=tuple(metadata.get("expected_indexes", ())),
                backend=metadata["backend"],
            )
        )
    return tuple(schemas)
