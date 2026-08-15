from pathlib import Path

from harness.cli import CommandResult
from tools.artifacts import ArtifactCollector


def test_artifact_collector_persists_command_and_worktree(tmp_path: Path):
    work = tmp_path / "work"
    work.mkdir()
    (work / "migration.sql").write_text("SELECT 1;\n", encoding="utf-8")
    result = CommandResult(("dbwarden", "migrate"), 1, "out", "err")

    bundle = ArtifactCollector().capture(
        result,
        work_dir=work,
        destination=tmp_path / "artifacts",
        extra_paths=(work / "migration.sql",),
    )
    assert bundle.stdout.read_text(encoding="utf-8") == "out"
    assert (bundle.directory / "migration.sql").exists()
    metadata = bundle.metadata.read_text(encoding="utf-8")
    assert '"work_dir"' in metadata


def test_artifact_collector_persists_provider_diagnostics_and_logs(tmp_path: Path):
    class Provider:
        def diagnostics(self):
            return {"image": "postgres:17", "container_id": "safe-id"}

        def logs(self):
            return "database ready\n"

    diagnostics, logs = ArtifactCollector().capture_provider(Provider(), tmp_path / "artifacts")

    assert '"container_id": "safe-id"' in diagnostics.read_text(encoding="utf-8")
    assert logs.read_text(encoding="utf-8") == "database ready\n"
