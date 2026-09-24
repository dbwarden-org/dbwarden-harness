from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from harness.cli import DbwardenCli
from mcp_server.dumper import dump_database_schema
from mcp_server.models import TrackResult
from mcp_server.workspace import Workspace


def run_track_a(
    workspace: Workspace, base_models_source: str, mutated_models_source: str
) -> TrackResult:
    work_dir = workspace.work_dir
    app_dir = work_dir / "app"
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "__init__.py").write_text("", encoding="utf-8")

    _write_config(work_dir, workspace.backend, workspace.track_a_url)

    cli = DbwardenCli(work_dir)

    init = cli.run("init", check=False)
    if init.returncode != 0:
        return TrackResult(success=False, stage="init", error=init.output)

    models_path = app_dir / "models.py"

    # Step 1: Establish baseline schema from base models.
    models_path.write_text(base_models_source, encoding="utf-8")
    made_base = cli.run("make-migrations", "base", check=False)
    if made_base.returncode != 0:
        return TrackResult(success=False, stage="make-migrations-base", error=made_base.output)
    migrated_base = cli.run("migrate", check=False)
    if migrated_base.returncode != 0:
        return TrackResult(success=False, stage="migrate-base", error=migrated_base.output)

    # Step 2: Mutate
    models_path.write_text(mutated_models_source, encoding="utf-8")

    # Step 3: Generate migration for the mutation
    made = cli.run("make-migrations", "ai_fuzz_test", check=False)
    if made.returncode != 0:
        return TrackResult(success=False, stage="make-migrations", error=made.output)

    # Step 4: Apply mutation migration
    migrated = cli.run("migrate", check=False)
    if migrated.returncode != 0:
        return TrackResult(success=False, stage="migrate", error=migrated.output)

    # Step 5: Dump schema and read plan
    try:
        schema_dump = dump_database_schema(workspace.track_a_url, workspace.backend)
    except Exception as error:  # noqa: BLE001
        return TrackResult(success=False, stage="schema-dump", error=str(error))

    plan = _read_latest_plan(work_dir)

    return TrackResult(
        success=True,
        stage="complete",
        schema_dump=schema_dump,
        plan=plan,
    )


def _write_config(work_dir: Path, backend: str, database_url: str) -> None:
    (work_dir / "dbwarden.py").write_text(
        "from dbwarden import database_config\n\n"
        "primary = database_config(\n"
        "    database_name='primary',\n"
        "    default=True,\n"
        f"    database_type={backend!r},\n"
        f"    database_url_sync={database_url!r},\n"
        "    model_paths=['app'],\n"
        ")\n",
        encoding="utf-8",
    )


def _read_latest_plan(work_dir: Path) -> dict[str, Any] | None:
    plans_dir = work_dir / "migrations" / "primary"
    if not plans_dir.exists():
        return None
    plans = sorted(plans_dir.glob("*.plan.json"))
    if not plans:
        return None
    try:
        return json.loads(plans[-1].read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
