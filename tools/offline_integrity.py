from __future__ import annotations

import hashlib
import json
from pathlib import Path


def state_files(work_dir: Path) -> tuple[Path, ...]:
    return tuple(
        sorted(
            path
            for path in (work_dir / ".dbwarden").glob("model_state*.json")
            if not path.name.endswith(".SHA256SUMS.json")
        )
    )


def build_state_manifest(work_dir: Path) -> dict[str, str]:
    files = state_files(work_dir)
    if not files:
        raise AssertionError(f"No exported model state found in {work_dir / '.dbwarden'}")
    return {
        path.relative_to(work_dir).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in files
    }


def write_state_manifest(work_dir: Path, destination: Path | None = None) -> Path:
    destination = destination or work_dir / ".dbwarden" / "model_state.SHA256SUMS.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(build_state_manifest(work_dir), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return destination


def verify_state_manifest(work_dir: Path, manifest: Path | None = None) -> None:
    manifest = manifest or work_dir / ".dbwarden" / "model_state.SHA256SUMS.json"
    expected = json.loads(manifest.read_text(encoding="utf-8"))
    actual = build_state_manifest(work_dir)
    if expected != actual:
        changed = sorted(
            path for path in set(expected) & set(actual) if expected[path] != actual[path]
        )
        raise AssertionError(f"Offline model-state checksum mismatch: changed={changed}")
