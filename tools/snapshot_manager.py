from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from difflib import unified_diff
from pathlib import Path


@dataclass(frozen=True)
class SQLSnapshot:
    relative_path: str
    content: str
    sha256: str


@dataclass(frozen=True)
class SnapshotDiff:
    expected: SQLSnapshot
    actual: SQLSnapshot

    @property
    def changed(self) -> bool:
        return self.expected.sha256 != self.actual.sha256

    @property
    def unified_text(self) -> str:
        return "".join(
            unified_diff(
                self.expected.content.splitlines(keepends=True),
                self.actual.content.splitlines(keepends=True),
                fromfile=self.expected.relative_path,
                tofile=self.actual.relative_path,
            )
        )


class SnapshotManager:
    def capture(self, migration_file: Path, *, root: Path | None = None) -> SQLSnapshot:
        content = migration_file.read_text(encoding="utf-8")
        relative = str(migration_file.relative_to(root)) if root else migration_file.name
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return SQLSnapshot(relative, content, digest)

    def compare(self, current: SQLSnapshot, baseline: SQLSnapshot) -> SnapshotDiff:
        return SnapshotDiff(baseline, current)

    def approve(self, diff: SnapshotDiff, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(diff.actual.content, encoding="utf-8")

    def assert_unchanged(self, diff: SnapshotDiff) -> None:
        if diff.changed:
            raise AssertionError(
                f"SQL snapshot changed for {diff.actual.relative_path}: "
                f"{diff.expected.sha256} -> {diff.actual.sha256}\n{diff.unified_text}"
            )

    def baseline_for(
        self,
        root: Path,
        *,
        version: str,
        backend: str,
        name: str,
    ) -> Path | None:
        """Return the approved baseline for one release, or None if unapproved.

        Generated SQL is a contract per release, not for all time: a backend fix
        legitimately changes the bytes, and a baseline captured two releases ago
        then reports every run as a regression. Baselines are stored under the
        exact version that produced them, with a ``major.minor`` series
        directory as a fallback for releases that share one contract.
        """
        candidates = [root / f"v{version}"]
        parts = version.split(".")
        if len(parts) >= 2:
            candidates.append(root / f"v{parts[0]}.{parts[1]}")
        for directory in candidates:
            baseline = directory / backend / name
            if baseline.exists():
                return baseline
        return None

    def build_manifest(self, root: Path) -> dict[str, str]:
        """Return stable SHA-256 checksums for every SQL snapshot below root."""
        return {
            path.relative_to(root).as_posix(): self.capture(path, root=root).sha256
            for path in sorted(root.rglob("*.sql"))
        }

    def write_manifest(self, root: Path, destination: Path | None = None) -> Path:
        destination = destination or root / "SHA256SUMS.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(self.build_manifest(root), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return destination

    def verify_manifest(self, root: Path, manifest: Path | None = None) -> None:
        manifest = manifest or root / "SHA256SUMS.json"
        expected = json.loads(manifest.read_text(encoding="utf-8"))
        actual = self.build_manifest(root)
        if expected != actual:
            missing = sorted(set(expected) - set(actual))
            unexpected = sorted(set(actual) - set(expected))
            changed = sorted(
                path for path in set(expected) & set(actual) if expected[path] != actual[path]
            )
            raise AssertionError(
                f"Snapshot manifest mismatch: missing={missing}, unexpected={unexpected}, changed={changed}"
            )
