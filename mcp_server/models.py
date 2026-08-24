from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class InitializeResult:
    workspace_id: str
    backend: str
    db_version: str | None
    work_dir: Path
    track_a_url: str
    track_b_url: str


@dataclass
class DestroyResult:
    workspace_id: str
    removed: bool


@dataclass
class WorkspaceInfo:
    workspace_id: str
    backend: str
    db_version: str | None
    work_dir: Path
    created_at: float
    frozen: bool


@dataclass
class ListWorkspacesResult:
    workspaces: list[WorkspaceInfo]


@dataclass
class WriteResult:
    workspace_id: str
    relative_path: str
    bytes_written: int


@dataclass
class MutationResult:
    workspace_id: str
    relative_path: str
    new_source: str
    applied: list[dict[str, Any]]


@dataclass
class TrackResult:
    success: bool
    stage: str
    error: str = ""
    schema_dump: str = ""
    schema_dump_path: Path | None = None
    plan: dict[str, Any] | None = None


@dataclass
class ComparisonSummary:
    missing_columns: list[dict[str, str]] = field(default_factory=list)
    type_mismatches: list[dict[str, str]] = field(default_factory=list)
    missing_tables: list[str] = field(default_factory=list)
    extra_tables: list[str] = field(default_factory=list)


@dataclass
class ComparisonResult:
    identical: bool
    diff: str = ""
    summary: ComparisonSummary = field(default_factory=ComparisonSummary)


@dataclass
class TwoTrackResult:
    passed: bool
    track_a: TrackResult
    track_b: TrackResult
    comparator: ComparisonResult
    classification: str
    proof_bundle_path: Path | None = None
    ai_may_inspect: bool = True
