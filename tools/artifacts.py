from __future__ import annotations

import json
import os
import platform
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from harness.cli import CommandResult
from harness.provenance import collect_provenance


@dataclass(frozen=True)
class ArtifactBundle:
    directory: Path
    stdout: Path
    stderr: Path
    metadata: Path
    copied_paths: tuple[Path, ...] = ()


class ArtifactCollector:
    """Persist enough CLI context to diagnose a failed black-box test."""

    def capture(
        self,
        result: CommandResult,
        *,
        work_dir: Path,
        destination: Path,
        extra_paths: tuple[Path, ...] = (),
        extra_metadata: dict[str, object] | None = None,
    ) -> ArtifactBundle:
        destination.mkdir(parents=True, exist_ok=True)
        stdout = destination / "stdout.txt"
        stderr = destination / "stderr.txt"
        metadata_path = destination / "command.json"
        provenance_path = destination / "provenance.json"
        stdout.write_text(result.stdout, encoding="utf-8")
        stderr.write_text(result.stderr, encoding="utf-8")
        sources = list(extra_paths)
        for default_path in (work_dir / "migrations", work_dir / ".dbwarden"):
            if default_path.exists() and default_path not in sources:
                sources.append(default_path)
        copied_paths: list[Path] = []
        metadata_path.write_text(
            json.dumps(
                {
                    "args": result.args,
                    "returncode": result.returncode,
                    "work_dir": str(work_dir),
                    "captured_paths": [str(path) for path in sources if path.exists()],
                    "runtime": {
                        "python": sys.version,
                        "platform": platform.platform(),
                    },
                    "harness_environment": {
                        key: value
                        for key, value in sorted(os.environ.items())
                        if key.startswith("DBWARDEN_HARNESS_")
                    },
                    "extra": extra_metadata or {},
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        provenance_path.write_text(
            json.dumps(
                collect_provenance(lockfile=Path(__file__).resolve().parents[1] / "uv.lock"),
                indent=2,
                default=list,
            )
            + "\n",
            encoding="utf-8",
        )
        for source in sources:
            if source.exists():
                relative = source.relative_to(work_dir) if source.is_relative_to(work_dir) else Path(source.name)
                target = destination / relative
                if source.is_dir():
                    shutil.copytree(source, target, dirs_exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
                copied_paths.append(target)
        return ArtifactBundle(destination, stdout, stderr, metadata_path, tuple(copied_paths))

    def capture_provider(self, provider: object, destination: Path) -> tuple[Path, Path]:
        """Persist safe provider diagnostics and logs without requiring a provider import."""
        destination.mkdir(parents=True, exist_ok=True)
        diagnostics_path = destination / "provider.json"
        logs_path = destination / "provider.log"
        diagnostics = getattr(provider, "diagnostics", dict)()
        logs = getattr(provider, "logs", lambda: "")()
        diagnostics_path.write_text(json.dumps(diagnostics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        logs_path.write_text(logs, encoding="utf-8")
        return diagnostics_path, logs_path
