import json
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text

from mcp_server import server
from mcp_server.workspace import Workspace, WorkspaceManager


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    root = tmp_path / "workspace"
    root.mkdir()
    url = f"sqlite:///{root / 'a.db'}"
    ws = Workspace("unit", "sqlite", "local", root, None, None, None, url, url)
    monkeypatch.setattr(server.WORKSPACES, "_workspaces", {"unit": ws})
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE items (id INTEGER)"))
        connection.execute(text("INSERT INTO items VALUES (1)"))
    engine.dispose()
    return ws


@pytest.mark.parametrize("path", ["../outside.txt", "../../escape", "/outside.txt", "C:/outside.txt"])
def test_workspace_files_reject_escape(workspace, path):
    for call in (lambda: server.write_model_file("unit", path, "bad"), lambda: server.read_file("unit", path)):
        with pytest.raises(ValueError, match="inside the workspace"):
            call()


def test_workspace_files_round_trip_and_freeze(workspace):
    server.write_model_file("unit", "app/models.py", "value = 1\n")
    assert json.loads(server.read_file("unit", "app/models.py"))["content"] == "value = 1\n"
    assert workspace.current_models_source == "value = 1\n"
    workspace.freeze()
    with pytest.raises(RuntimeError, match="frozen"):
        server.write_model_file("unit", "app/models.py", "value = 2\n")


@pytest.mark.parametrize("sql", ["DELETE FROM items", "DROP TABLE items", "PRAGMA query_only = OFF", "SELECT 1; DELETE FROM items", "WITH x AS (SELECT 1) DELETE FROM items", "SELECT * INTO backup FROM items"])
def test_read_only_rejects_writes(workspace, sql):
    workspace.freeze()
    with pytest.raises(ValueError, match="read_only"):
        server.query_database("unit", sql)
    assert json.loads(server.query_database("unit", "SELECT * FROM items"))["rows"] == [{"id": 1}]


def test_query_writes_commit_and_return_rows(workspace):
    result = json.loads(server.query_database("unit", "INSERT INTO items VALUES (2)", read_only=False))
    assert result["rows"] == []
    assert json.loads(server.query_database("unit", "SELECT id FROM items ORDER BY id"))["rows"] == [{"id": 1}, {"id": 2}]
    workspace.freeze()
    with pytest.raises(RuntimeError, match="frozen"):
        server.query_database("unit", "DELETE FROM items", read_only=False)


@pytest.mark.parametrize("prefix", ["../escape", "/root", "C:\\temp", "", "a" * 65])
def test_workspace_prefix_validation(tmp_path, monkeypatch, prefix):
    monkeypatch.setattr("mcp_server.workspace.CONFIG", SimpleNamespace(max_workspaces=1, db_versions={"sqlite": "local"}, workspace_root=tmp_path))
    with pytest.raises(ValueError, match="name_prefix"):
        WorkspaceManager().initialize("sqlite", name_prefix=prefix)
    assert list(tmp_path.iterdir()) == []


def test_invalid_reference_mode_fails_before_running_tracks(workspace):
    with pytest.raises(ValueError, match="reference_mode"):
        server.run_two_track_test("unit", "typo")


def test_track_a_reads_adjacent_plan(tmp_path):
    from mcp_server.track_a import _read_latest_plan
    directory = tmp_path / "migrations/primary"
    directory.mkdir(parents=True)
    plan = {"severity": {"file": "INFO"}, "upgrade_ops": []}
    (directory / "primary__0001_create.plan.json").write_text(json.dumps(plan), encoding="utf-8")
    assert _read_latest_plan(tmp_path) == plan
