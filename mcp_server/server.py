from __future__ import annotations

import atexit
import json
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from sqlalchemy import create_engine, text

from mcp_server.bundle import assemble_proof_bundle
from mcp_server.comparator import compare_schemas
from mcp_server.models import (
    ComparisonResult,
    TrackResult,
    TwoTrackResult,
)
from mcp_server.mutations import apply_mutation as apply_model_mutation
from mcp_server.pool import POOL
from mcp_server.track_a import run_track_a
from mcp_server.track_b import run_track_b_incremental, run_track_b_nuclear
from mcp_server.workspace import WORKSPACES, Workspace

mcp = FastMCP("dbwarden-harness")
POOL.start()


def _cleanup() -> None:
    for ws in list(WORKSPACES._workspaces.values()):
        WORKSPACES.destroy(ws.workspace_id)
    POOL.stop()


atexit.register(_cleanup)


def _require_workspace(workspace_id: str) -> Workspace:
    return WORKSPACES.get(workspace_id)


def _write_model_file_internal(workspace: Workspace, relative_path: str, content: str) -> Path:
    if workspace.frozen:
        raise RuntimeError(f"Workspace {workspace.workspace_id!r} is frozen")
    path = workspace.work_dir / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if relative_path.replace("\\", "/").endswith("app/models.py"):
        if workspace.base_models_source is None:
            workspace.base_models_source = content
        workspace.current_models_source = content
    return path


@mcp.tool()
def initialize_workspace(
    backend: str,
    db_version: str | None = None,
    name_prefix: str | None = None,
) -> str:
    """Create a new isolated workspace with a database pair for two-track testing."""
    result = WORKSPACES.initialize(backend, db_version, name_prefix)
    return json.dumps(
        {
            "workspace_id": result.workspace_id,
            "backend": result.backend,
            "db_version": result.db_version,
            "work_dir": str(result.work_dir),
            "track_a_url": result.track_a_url,
            "track_b_url": result.track_b_url,
        }
    )


@mcp.tool()
def destroy_workspace(workspace_id: str) -> str:
    """Destroy a workspace and release its resources."""
    result = WORKSPACES.destroy(workspace_id)
    return json.dumps({"workspace_id": result.workspace_id, "removed": result.removed})


@mcp.tool()
def list_workspaces() -> str:
    """List all active workspaces."""
    result = WORKSPACES.list_workspaces()
    return json.dumps(
        [
            {
                "workspace_id": ws.workspace_id,
                "backend": ws.backend,
                "db_version": ws.db_version,
                "work_dir": str(ws.work_dir),
                "created_at": ws.created_at,
                "frozen": ws.frozen,
            }
            for ws in result.workspaces
        ]
    )


@mcp.tool()
def write_model_file(workspace_id: str, relative_path: str, content: str) -> str:
    """Write a file inside a workspace; app/models.py also updates the test model state."""
    workspace = _require_workspace(workspace_id)
    path = _write_model_file_internal(workspace, relative_path, content)
    return json.dumps(
        {
            "workspace_id": workspace_id,
            "relative_path": relative_path,
            "bytes_written": path.stat().st_size,
        }
    )


@mcp.tool()
def apply_mutation(workspace_id: str, mutation: dict[str, Any]) -> str:
    """Apply a structured mutation to the current app/models.py."""
    workspace = _require_workspace(workspace_id)
    if workspace.frozen:
        raise RuntimeError(f"Workspace {workspace.workspace_id!r} is frozen")

    models_path = workspace.work_dir / "app" / "models.py"
    source = models_path.read_text(encoding="utf-8") if models_path.exists() else ""
    new_source = apply_model_mutation(source, mutation)
    _write_model_file_internal(workspace, "app/models.py", new_source)
    workspace.mutations.append(mutation)

    return json.dumps(
        {
            "workspace_id": workspace_id,
            "relative_path": "app/models.py",
            "new_source": new_source,
            "applied": workspace.mutations,
        }
    )


@mcp.tool()
def run_two_track_test(
    workspace_id: str,
    reference_mode: str = "nuclear",
) -> str:
    """Run dbwarden (Track A) and a SQLAlchemy Core DDL reference (Track B), then compare schemas."""
    workspace = _require_workspace(workspace_id)
    if workspace.frozen:
        raise RuntimeError(f"Workspace {workspace.workspace_id!r} is frozen")

    current = workspace.current_models_source
    if current is None:
        raise RuntimeError(f"Workspace {workspace_id!r} has no model file")
    base = workspace.base_models_source or current

    track_a_result = run_track_a(workspace, base, current)
    if not track_a_result.success:
        comparison = ComparisonResult(identical=False)
        return json.dumps(
            _two_track_result_to_dict(
                TwoTrackResult(
                    passed=False,
                    track_a=track_a_result,
                    track_b=TrackResult(success=False, stage="not-run", error="Track A failed"),
                    comparator=comparison,
                    classification="95" if track_a_result.plan is None else "5",
                )
            )
        )

    if reference_mode == "incremental":
        track_b_result = run_track_b_incremental(workspace, base, current)
    else:
        track_b_result = run_track_b_nuclear(workspace, current)

    if not track_b_result.success:
        comparison = ComparisonResult(identical=False)
        return json.dumps(
            _two_track_result_to_dict(
                TwoTrackResult(
                    passed=False,
                    track_a=track_a_result,
                    track_b=track_b_result,
                    comparator=comparison,
                    classification="5",
                )
            )
        )

    comparison = compare_schemas(
        track_a_result.schema_dump, track_b_result.schema_dump, backend=workspace.backend
    )

    if comparison.identical:
        result = TwoTrackResult(
            passed=True,
            track_a=track_a_result,
            track_b=track_b_result,
            comparator=comparison,
            classification="95",
        )
    else:
        result = assemble_proof_bundle(
            workspace,
            base,
            current,
            track_a_result,
            track_b_result,
            comparison,
            reference_mode,
        )

    return json.dumps(_two_track_result_to_dict(result))


def _two_track_result_to_dict(result: TwoTrackResult) -> dict[str, Any]:
    return {
        "passed": result.passed,
        "track_a": {
            "success": result.track_a.success,
            "stage": result.track_a.stage,
            "error": result.track_a.error,
            "schema_dump_path": str(result.track_a.schema_dump_path) if result.track_a.schema_dump_path else None,
            "plan": result.track_a.plan,
        },
        "track_b": {
            "success": result.track_b.success,
            "stage": result.track_b.stage,
            "error": result.track_b.error,
            "schema_dump_path": str(result.track_b.schema_dump_path) if result.track_b.schema_dump_path else None,
        },
        "comparator": {
            "identical": result.comparator.identical,
            "diff": result.comparator.diff,
            "summary": {
                "missing_columns": result.comparator.summary.missing_columns,
                "type_mismatches": result.comparator.summary.type_mismatches,
                "missing_tables": result.comparator.summary.missing_tables,
                "extra_tables": result.comparator.summary.extra_tables,
            },
        },
        "classification": result.classification,
        "proof_bundle_path": str(result.proof_bundle_path) if result.proof_bundle_path else None,
        "ai_may_inspect": result.ai_may_inspect,
    }


@mcp.tool()
def read_file(workspace_id: str, relative_path: str) -> str:
    """Read a file from a workspace (read-only; works on frozen workspaces)."""
    workspace = _require_workspace(workspace_id)
    path = workspace.work_dir / relative_path
    if not path.exists():
        raise FileNotFoundError(f"{relative_path!r} not found in workspace {workspace_id!r}")
    content = path.read_text(encoding="utf-8")
    return json.dumps({"workspace_id": workspace_id, "relative_path": relative_path, "content": content})


@mcp.tool()
def inspect_schema(workspace_id: str) -> str:
    """Return native schema dumps for both tracks (read-only)."""
    workspace = _require_workspace(workspace_id)
    from mcp_server.dumper import dump_database_schema

    try:
        track_a_dump = dump_database_schema(workspace.track_a_url, workspace.backend)
    except Exception as error:  # noqa: BLE001
        track_a_dump = f"ERROR: {error}"
    try:
        track_b_dump = dump_database_schema(workspace.track_b_url, workspace.backend)
    except Exception as error:  # noqa: BLE001
        track_b_dump = f"ERROR: {error}"

    return json.dumps(
        {
            "workspace_id": workspace_id,
            "track_a_schema_dump": track_a_dump,
            "track_b_schema_dump": track_b_dump,
        }
    )


@mcp.tool()
def query_database(workspace_id: str, sql: str, read_only: bool = True) -> str:
    """Run a SQL query against Track A's database. Defaults to read-only."""
    workspace = _require_workspace(workspace_id)
    if workspace.frozen and not read_only:
        raise RuntimeError("Cannot write to a frozen workspace")

    engine = create_engine(workspace.track_a_url)
    try:
        with engine.connect() as connection:
            if read_only:
                result = connection.execute(text(sql))
            else:
                with connection.begin():
                    result = connection.execute(text(sql))
            rows = [dict(row._mapping) for row in result.mappings()]
            return json.dumps({"workspace_id": workspace_id, "read_only": read_only, "rows": rows})
    finally:
        engine.dispose()


def run_server() -> None:
    mcp.run()
