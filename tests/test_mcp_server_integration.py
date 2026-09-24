from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from mcp_server.server import (
    apply_mutation,
    destroy_workspace,
    initialize_workspace,
    run_two_track_test,
    write_model_file,
)


@pytest.fixture(autouse=True)
def isolated_workspaces(tmp_path, monkeypatch):
    from dataclasses import replace

    from mcp_server.workspace import CONFIG

    monkeypatch.setattr("mcp_server.workspace.CONFIG", replace(CONFIG, workspace_root=tmp_path))
    monkeypatch.setenv("DBWARDEN_HARNESS_BUG_REPORTS_DIR", str(tmp_path / "bug-reports"))


BASE_MODELS = """\
from sqlalchemy import Integer, String, MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention={"uq": "uq_%(table_name)s_%(column_0_name)s"})


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
"""


def test_sqlite_two_track_add_column() -> None:
    """End-to-end two-track test on SQLite: add a column and require convergence."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["DBWARDEN_HARNESS_ROOT"] = tmp
        os.environ["DBWARDEN_HARNESS_BUG_REPORTS_DIR"] = str(Path(tmp) / "bug-reports")

        init_raw = initialize_workspace("sqlite")
        init = json.loads(init_raw)
        workspace_id = init["workspace_id"]

        try:
            write_model_file(workspace_id, "app/models.py", BASE_MODELS)
            apply_mutation(
                workspace_id,
                {"type": "add_column", "table": "users", "column": "bio", "column_type": "String"},
            )
            result_raw = run_two_track_test(workspace_id, reference_mode="nuclear")
            result = json.loads(result_raw)

            assert result["passed"] is True, json.dumps(result, indent=2)
            assert result["comparator"]["identical"] is True
            assert result["classification"] == "95"
        finally:
            destroy_workspace(workspace_id)


def test_sqlite_two_track_incremental() -> None:
    """End-to-end two-track test using the incremental reference path."""
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["DBWARDEN_HARNESS_ROOT"] = tmp
        os.environ["DBWARDEN_HARNESS_BUG_REPORTS_DIR"] = str(Path(tmp) / "bug-reports")

        init_raw = initialize_workspace("sqlite")
        init = json.loads(init_raw)
        workspace_id = init["workspace_id"]

        try:
            write_model_file(workspace_id, "app/models.py", BASE_MODELS)
            apply_mutation(
                workspace_id,
                {"type": "add_column", "table": "users", "column": "bio", "column_type": "String"},
            )
            result_raw = run_two_track_test(workspace_id, reference_mode="incremental")
            result = json.loads(result_raw)

            assert result["passed"] is True, json.dumps(result, indent=2)
            assert result["comparator"]["identical"] is True
        finally:
            destroy_workspace(workspace_id)
