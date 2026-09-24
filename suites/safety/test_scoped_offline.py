import json
import subprocess

from tools.migration_player import MigrationPlayer
from tools.sql_probe import SqlProbe


def models(extra="", obsolete=True):
    return (
        "from sqlalchemy import Column, Integer, String\n"
        "from sqlalchemy.orm import declarative_base\n"
        "Base = declarative_base()\n"
        "class Item(Base):\n"
        "    __tablename__ = 'items'\n"
        "    id = Column(Integer, primary_key=True)\n"
        + extra
        + ("class Obsolete(Base):\n    __tablename__ = 'obsolete'\n    id = Column(Integer, primary_key=True)\n" if obsolete else "")
    )


def project(tmp_path):
    player = MigrationPlayer(f"sqlite:///{tmp_path / 'app.db'}", tmp_path)
    player.write_model_source(models(), filename="app/models.py")
    player.init_and_configure(model_paths=("app",))
    player.export_models()
    player.make_migrations("initial", "--offline")
    assert not (tmp_path / "app.db").exists()
    return player


def test_offline_split_scope_stops_then_resumes_with_valid_state(tmp_path):
    player = project(tmp_path)
    player.migrate()
    player.write_model_source(models("    nickname = Column(String(30))\n", False), filename="app/models.py")
    player.make_migrations("scoped", "--offline", "--split-at-severity", "WARN")
    paths = sorted((tmp_path / "migrations/primary").glob("*.sql"))
    assert len(paths) == 3
    assert "ADD COLUMN" in paths[1].read_text()
    assert "DROP TABLE" not in paths[1].read_text().split("-- rollback")[0]
    assert "DROP TABLE obsolete" in paths[2].read_text()
    plans = [json.loads(p.with_suffix(".plan.json").read_text()) for p in paths]
    assert [p["severity"]["file"] for p in plans] == ["INFO", "INFO", "CRITICAL"]
    assert plans[1]["target_checksum"] == plans[2]["base_checksum"]
    stopped = player.cli.run("migrate", "--max-severity", "INFO", "--force", check=False)
    assert stopped.returncode == 3, stopped.output
    with SqlProbe(player.database_url) as probe:
        assert probe.rows("SELECT name FROM sqlite_master WHERE name='obsolete'") == [("obsolete",)]
        assert "nickname" in [row[1] for row in probe.rows("PRAGMA table_info(items)")]
    player.migrate("--force")
    player.assert_converged()
    before = {p: p.read_bytes() for p in (tmp_path / "migrations").rglob("*") if p.is_file()}
    player.make_migrations("unchanged", "--offline", "--split-at-severity", "WARN")
    assert {p: p.read_bytes() for p in (tmp_path / "migrations").rglob("*") if p.is_file()} == before
    state = json.loads((tmp_path / ".dbwarden/model_state.primary.json").read_text())
    assert "obsolete" not in state["tables"]
    assert json.loads((tmp_path / ".dbwarden/model_state.json").read_text()) == state


def test_malformed_plan_defers_all_later_files(tmp_path):
    player = project(tmp_path)
    path = next((tmp_path / "migrations/primary").glob("*.plan.json"))
    path.write_text('{"severity": []}', encoding="utf-8")
    stopped = player.cli.run("migrate", "--max-severity", "WARN", "--force", check=False)
    assert stopped.returncode == 3, stopped.output
    assert "UNKNOWN" in stopped.output
    with SqlProbe(player.database_url) as probe:
        assert probe.rows("SELECT name FROM sqlite_master WHERE name='items'") == []


def test_git_merge_preserves_offline_state_and_sql_pairs(tmp_path):
    player = project(tmp_path)

    def git(*args, check=True):
        return subprocess.run(["git", "-c", "user.name=Harness", "-c", "user.email=harness@example.invalid", "-c", "commit.gpgsign=false", *args], cwd=tmp_path, text=True, capture_output=True, check=check)

    git("init", "-q", "-b", "left")
    (tmp_path / ".gitignore").write_text("__pycache__/\n*.pyc\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-qm", "baseline")
    git("branch", "right")
    player.write_model_source(models("    nickname = Column(String(30))\n", False), filename="app/models.py")
    player.make_migrations("left", "--offline", "--split-at-severity", "WARN")
    git("add", ".")
    git("commit", "-qm", "left changes")
    git("switch", "right")
    player.write_model_source(models("    age = Column(Integer)\n"), filename="app/models.py")
    player.make_migrations("right", "--offline")
    git("add", ".")
    git("commit", "-qm", "right changes")
    git("switch", "left")
    merged = git("merge", "--no-commit", "right", check=False)
    assert merged.returncode in (0, 1), merged.stderr
    player.write_model_source(models("    nickname = Column(String(30))\n    age = Column(Integer)\n", False), filename="app/models.py")
    for name in ("model_state.primary.json", "model_state.json"):
        path = tmp_path / ".dbwarden" / name
        path.write_text(git("show", f"HEAD:.dbwarden/{name}").stdout, encoding="utf-8")
    git("add", ".")
    git("commit", "-qm", "merge models")
    before = {p: p.read_bytes() for root in (tmp_path / "migrations", tmp_path / ".dbwarden") for p in root.rglob("*") if p.is_file()}
    player.cli.run("merge", "--dry-run", "--split-at-severity", "WARN")
    assert {p: p.read_bytes() for root in (tmp_path / "migrations", tmp_path / ".dbwarden") for p in root.rglob("*") if p.is_file()} == before
    player.cli.run("merge", "--split-at-severity", "WARN")
    records = list((tmp_path / ".dbwarden/merges").glob("*.json"))
    assert len(records) == 1
    record = json.loads(records[0].read_text())
    assert len(record["superseded_files"]) == 3
    assert len(record["reconciliation_files"]) == 2
    player.migrate("--force")
    player.assert_converged()
    state = json.loads((tmp_path / ".dbwarden/model_state.primary.json").read_text())
    assert json.loads((tmp_path / ".dbwarden/model_state.json").read_text()) == state
    assert set(state["tables"]["items"]["columns"]) == {"id", "nickname", "age"}
    assert "obsolete" not in state["tables"]


import pytest


@pytest.fixture(autouse=True)
def _close_leaked_sqlite_connections():
    """The suite relies on sqlite context-manager commits, which never close."""
    yield
    import gc
    import sqlite3
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for obj in gc.get_objects():
            if isinstance(obj, sqlite3.Connection):
                try:
                    obj.close()
                except Exception:
                    pass
