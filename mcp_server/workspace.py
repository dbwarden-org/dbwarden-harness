from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from infrastructure.providers.base import DatabaseProvider
from infrastructure.providers.sqlite import SQLiteProvider
from mcp_server.config import CONFIG
from mcp_server.models import DestroyResult, InitializeResult, ListWorkspacesResult, WorkspaceInfo
from mcp_server.network import WorkspaceNetwork
from mcp_server.pool import POOL


@dataclass
class Workspace:
    workspace_id: str
    backend: str
    db_version: str | None
    work_dir: Path
    network: WorkspaceNetwork | None
    track_a_provider: DatabaseProvider
    track_b_provider: DatabaseProvider
    track_a_url: str
    track_b_url: str
    created_at: float = field(default_factory=time.time)
    frozen: bool = False
    mutations: list[dict[str, Any]] = field(default_factory=list)
    base_models_source: str | None = None
    current_models_source: str | None = None

    def freeze(self) -> None:
        self.frozen = True


class WorkspaceManager:
    """Create, track, and destroy isolated per-test workspaces."""

    def __init__(self) -> None:
        self._workspaces: dict[str, Workspace] = {}

    def initialize(
        self,
        backend: str,
        db_version: str | None = None,
        name_prefix: str | None = None,
    ) -> InitializeResult:
        if len(self._workspaces) >= CONFIG.max_workspaces:
            raise RuntimeError(f"Maximum number of workspaces ({CONFIG.max_workspaces}) reached")

        backend = backend.lower()
        if backend == "postgres":
            backend = "postgresql"

        resolved_version = db_version or CONFIG.db_versions.get(backend)
        workspace_id = f"{name_prefix or 'ws'}-{uuid.uuid4().hex[:8]}"
        work_dir = CONFIG.workspace_root / workspace_id
        work_dir.mkdir(parents=True, exist_ok=True)

        network: WorkspaceNetwork | None = None
        if backend == "sqlite":
            track_a_provider = SQLiteProvider(work_dir / "track_a.db")
            track_b_provider = SQLiteProvider(work_dir / "track_b.db")
            track_a_url = track_a_provider.start()
            track_b_url = track_b_provider.start()
        else:
            network = WorkspaceNetwork.create()
            track_a_provider = POOL.claim(backend, resolved_version or "latest", network)
            track_b_provider = POOL.claim(backend, resolved_version or "latest", network)
            track_a_url = track_a_provider.url()
            track_b_url = track_b_provider.url()

        workspace = Workspace(
            workspace_id=workspace_id,
            backend=backend,
            db_version=resolved_version,
            work_dir=work_dir,
            network=network,
            track_a_provider=track_a_provider,
            track_b_provider=track_b_provider,
            track_a_url=track_a_url,
            track_b_url=track_b_url,
        )
        self._workspaces[workspace_id] = workspace

        return InitializeResult(
            workspace_id=workspace_id,
            backend=backend,
            db_version=resolved_version,
            work_dir=work_dir,
            track_a_url=track_a_url,
            track_b_url=track_b_url,
        )

    def destroy(self, workspace_id: str) -> DestroyResult:
        workspace = self._workspaces.pop(workspace_id, None)
        if workspace is None:
            return DestroyResult(workspace_id=workspace_id, removed=False)

        if workspace.backend == "sqlite":
            workspace.track_a_provider.stop()
            workspace.track_b_provider.stop()
        else:
            POOL.release(workspace.backend, workspace.track_a_provider, workspace.network)
            POOL.release(workspace.backend, workspace.track_b_provider, workspace.network)
            if workspace.network is not None:
                workspace.network.remove()

        return DestroyResult(workspace_id=workspace_id, removed=True)

    def list_workspaces(self) -> ListWorkspacesResult:
        return ListWorkspacesResult(
            workspaces=[
                WorkspaceInfo(
                    workspace_id=ws.workspace_id,
                    backend=ws.backend,
                    db_version=ws.db_version,
                    work_dir=ws.work_dir,
                    created_at=ws.created_at,
                    frozen=ws.frozen,
                )
                for ws in self._workspaces.values()
            ]
        )

    def get(self, workspace_id: str) -> Workspace:
        workspace = self._workspaces.get(workspace_id)
        if workspace is None:
            raise KeyError(f"Workspace {workspace_id!r} not found")
        return workspace


WORKSPACES = WorkspaceManager()
