import json
import sqlite3
from pathlib import Path

from tools.migration_player import MigrationPlayer

MODELS = '''from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from dbwarden.data import DataMeta, rows
class Base(DeclarativeBase): pass
class Country(Base):
    __tablename__ = "countries"
    code: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    class Data(DataMeta):
        managed_rows = rows(key="code", rows=[{"code": "UY", "name": "Uruguay"}], owned_columns=["name"], rollback="restore_previous")
'''

PARAMETER_MODELS = '''from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from dbwarden.data import DataMeta, derive, param, rows
class Base(DeclarativeBase): pass
class Country(Base):
    __tablename__ = "countries"
    code: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    label: Mapped[str | None] = mapped_column(String)
    class Data(DataMeta):
        managed_rows = rows(key="code", rows=[{"code": "UY", "name": "Uruguay"}], owned_columns=["name"], rollback="restore_previous")
        transformations = [derive("label", param("label", str), rollback="clear")]
'''

SOURCE_AND_TARGET_MODELS = '''from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
class Base(DeclarativeBase): pass
class Legacy(Base):
    __tablename__ = "legacy"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
class Country(Base):
    __tablename__ = "countries"
    code: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
'''

COUNTRY_MODEL = '''from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
class Base(DeclarativeBase): pass
class Country(Base):
    __tablename__ = "countries"
    code: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
'''

CURRENT_SOURCE_MODEL = '''from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
class Base(DeclarativeBase): pass
class Legacy(Base):
    __tablename__ = "legacy"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
'''

CURRENT_SOURCE_AND_TARGET_MODELS = '''from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
class Base(DeclarativeBase): pass
class Legacy(Base):
    __tablename__ = "legacy"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
class Country(Base):
    __tablename__ = "countries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
'''

CAPTURE_SOURCE_MODEL = '''from sqlalchemy import Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
class Base(DeclarativeBase): pass
class Item(Base):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[int] = mapped_column(Integer, nullable=False)
    value: Mapped[int] = mapped_column(Integer, nullable=False)
'''

CAPTURE_MODEL = '''from sqlalchemy import Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from dbwarden.data import DataMeta, col, derive
class Base(DeclarativeBase): pass
class Item(Base):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[int] = mapped_column(Integer, nullable=False)
    value: Mapped[int] = mapped_column(Integer, nullable=False)
    class Data(DataMeta):
        transformations = [derive("value", col("source") + 1, rollback="capture")]
'''

MERGE_SOURCES = '''from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
class Base(DeclarativeBase): pass
class LegacyA(Base):
    __tablename__ = "legacy_a"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
class LegacyB(Base):
    __tablename__ = "legacy_b"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
'''

MERGE_TARGET = '''from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
class Base(DeclarativeBase): pass
class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    total: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
'''


def _merged_transition(snapshot_id: str) -> str:
    return f'''from app.models import Account
from dbwarden.data import DataTransition, aggregate, batch, col, from_source, historical_table, into, merge_sources, winner
left = historical_table("legacy_a", snapshot={snapshot_id!r})
right = historical_table("legacy_b", snapshot={snapshot_id!r})
source = merge_sources(
    from_source(left, identity=["id"], map={{"id": col("account"), "amount": col("amount"), "name": col("name")}}, priority=0),
    from_source(right, identity=["id"], map={{"id": col("account"), "amount": col("amount"), "name": col("name")}}, priority=1),
    key=["id"], values={{"total": aggregate("sum", col("amount")), "name": winner(col("name"))}},
)
class Consolidate(DataTransition):
    source = source
    targets = [into(Account, map={{Account.id: col("id"), Account.total: col("total"), Account.name: col("name")}}, key=[Account.id])]
    execution = batch(size=2, key=["id"])
'''


def _transition(snapshot_id: str, *, conflict: str = "ignore_if_equivalent") -> str:
    return f'''from app.models import Country
from dbwarden.data import DataTransition, historical_table, into
old = historical_table("legacy", snapshot={snapshot_id!r})
class MoveLegacy(DataTransition):
    source = old
    source_identity = [old.id]
    targets = [into(Country, map={{Country.code: old.code, Country.name: old.name}}, key=[Country.code], on_conflict={conflict!r})]
'''


def _current_source_transition(snapshot_id: str) -> str:
    return f'''from app.models import Country, Legacy
from dbwarden.data import DataTransition, into
class CopyCurrent(DataTransition):
    source = Legacy
    source_snapshot = {snapshot_id!r}
    source_identity = [Legacy.id]
    on_complete = "keep"
    targets = [into(Country, map={{Country.id: Legacy.id, Country.name: Legacy.name}}, key=[Country.id])]
'''


def _scoped_rows(rows: list[dict[str, str]]) -> str:
    return f'''from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from dbwarden.data import DataMeta, col, literal, rows
class Base(DeclarativeBase): pass
class Country(Base):
    __tablename__ = "countries"
    code: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    class Data(DataMeta):
        managed_rows = rows(key="code", rows={rows!r}, owned_columns=["name"], on_missing="delete", scope=col("code") != literal(""), acknowledge_delete=True, rollback="restore_previous")
'''


def _archived_rows(rows: list[dict[str, str]]) -> str:
    return f'''from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from dbwarden.data import DataMeta, archive_table, col, literal, rows
class Base(DeclarativeBase): pass
class Item(Base):
    __tablename__ = "items"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    note: Mapped[str | None] = mapped_column(String)
    class Data(DataMeta):
        managed_rows = rows(key="id", rows={rows!r}, owned_columns=["name"], on_missing="archive", scope=col("id") != literal(""), archive_to=archive_table("items_archive"), acknowledge_archive=True, rollback="restore_previous")
'''


def _snapshot_id(work_dir: Path) -> str:
    registry = json.loads(
        (work_dir / ".dbwarden" / "snapshots" / "registry.json").read_text(encoding="utf-8")
    )
    return registry["snapshots"][-1]["snapshot_id"]


def _transition_project(tmp_path: Path) -> tuple[MigrationPlayer, Path]:
    database = tmp_path / "transition.db"
    player = MigrationPlayer(f"sqlite:///{database}", tmp_path)
    player.write_model_source("", filename="app/__init__.py")
    player.write_model_source("", filename="transitions/__init__.py")
    player.write_model_source(SOURCE_AND_TARGET_MODELS, filename="app/models.py")
    player.init_and_configure(model_paths=("app",), data_paths=["transitions"])
    assert player.make_migrations("legacy schema").returncode == 0
    assert player.migrate("--force").returncode == 0
    return player, database


def test_sqlite_data_bundle_applies_rolls_back_reapplies_and_tamper_fails(tmp_path: Path):
    database = tmp_path / "data.db"
    player = MigrationPlayer(f"sqlite:///{database}", tmp_path)
    player.write_model_source("", filename="app/__init__.py")
    player.write_model_source(MODELS, filename="app/models.py")
    player.init_and_configure(model_paths=("app",))
    assert player.export_models().returncode == 0
    assert player.make_migrations("country data", "--offline").returncode == 0
    sql = next((tmp_path / "migrations" / "primary").glob("*.sql"))
    assert sql.with_suffix(".data.py").exists()
    original = sql.read_text(encoding="utf-8")
    sql.write_text(original + "\n-- tampered\n", encoding="utf-8")
    failed = player.cli.run("migrate", "--dry-run", "--data", check=False)
    assert failed.returncode != 0
    assert "hash mismatch" in failed.output.lower()
    sql.write_text(original, encoding="utf-8")
    assert player.migrate("--force").returncode == 0
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT code, name FROM countries").fetchall() == [("UY", "Uruguay")]
    assert player.rollback().returncode == 0
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'countries'"
        ).fetchall() == []
    assert player.migrate("--reapply-data").returncode == 0
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT code, name FROM countries").fetchall() == [("UY", "Uruguay")]


def test_sqlite_data_parameter_is_required_frozen_and_applied(tmp_path: Path):
    database = tmp_path / "parameter.db"
    player = MigrationPlayer(f"sqlite:///{database}", tmp_path)
    player.write_model_source("", filename="app/__init__.py")
    player.write_model_source(PARAMETER_MODELS, filename="app/models.py")
    player.init_and_configure(model_paths=("app",))
    assert player.export_models().returncode == 0
    missing = player.cli.run("make-migrations", "parameter data", "--offline", check=False)
    assert missing.returncode != 0
    assert "parameter" in missing.output.lower()
    assert player.make_migrations(
        "parameter data", "--offline", "--param", 'label="Latin America"'
    ).returncode == 0
    frozen = next((tmp_path / "migrations" / "primary").glob("*.data.py"))
    assert "Latin America" in frozen.read_text(encoding="utf-8")
    preview = player.cli.run("migrate", "--dry-run", "--data")
    assert "data" in preview.output.lower()
    assert player.migrate("--force").returncode == 0
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT code, name, label FROM countries").fetchall() == [
            ("UY", "Uruguay", "Latin America")
        ]
    assert player.cli.run("check", "--data").returncode == 0


def test_sqlite_scoped_managed_row_delete_keeps_unowned_rows(tmp_path: Path):
    database = tmp_path / "scoped.db"
    player = MigrationPlayer(f"sqlite:///{database}", tmp_path)
    player.write_model_source("", filename="app/__init__.py")
    player.write_model_source(
        _scoped_rows([
            {"code": "AR", "name": "Argentina"},
            {"code": "UY", "name": "Uruguay"},
        ]),
        filename="app/models.py",
    )
    player.init_and_configure(model_paths=("app",))
    assert player.export_models().returncode == 0
    assert player.make_migrations("initial countries", "--offline").returncode == 0
    assert player.migrate("--force").returncode == 0
    with sqlite3.connect(database) as connection:
        connection.execute("INSERT INTO countries VALUES ('BR', 'Brazil')")
        connection.commit()
    player.write_model_source(
        _scoped_rows([{"code": "UY", "name": "Uruguay"}]), filename="app/models.py"
    )
    assert player.make_migrations("remove Argentina").returncode == 0
    assert player.migrate("--force").returncode == 0
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT code, name FROM countries ORDER BY code").fetchall() == [
            ("BR", "Brazil"),
            ("UY", "Uruguay"),
        ]
    player.assert_converged()


def test_sqlite_managed_archive_round_trips_through_cli(tmp_path: Path):
    database = tmp_path / "archive.db"
    player = MigrationPlayer(f"sqlite:///{database}", tmp_path)
    player.write_model_source("", filename="app/__init__.py")
    player.write_model_source(_archived_rows([{"id": "old", "name": "Old"}]), filename="app/models.py")
    player.init_and_configure(model_paths=("app",))
    assert player.export_models().returncode == 0
    assert player.make_migrations("initial archive rows", "--offline").returncode == 0
    assert player.migrate("--force").returncode == 0
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE items SET note = 'application note' WHERE id = 'old'")
        connection.commit()
    player.write_model_source(_archived_rows([]), filename="app/models.py")
    assert player.make_migrations("archive old row").returncode == 0
    assert player.cli.run("data", "render", "--format", "json").returncode == 0
    assert player.migrate("--force").returncode == 0
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT * FROM items").fetchall() == []
        assert connection.execute("SELECT id,name,note FROM items_archive").fetchall() == [("old", "Old", "application note")]
    assert player.cli.run("check", "--data").returncode == 0
    assert player.rollback().returncode == 0
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT id,name,note FROM items").fetchall() == [("old", "Old", "application note")]
    assert player.migrate("--force", "--reapply-data").returncode == 0


def test_sqlite_many_source_merge_batches_and_round_trips(tmp_path: Path):
    database = tmp_path / "merge.db"
    player = MigrationPlayer(f"sqlite:///{database}", tmp_path)
    player.write_model_source("", filename="app/__init__.py")
    player.write_model_source("", filename="transitions/__init__.py")
    player.write_model_source(MERGE_SOURCES, filename="app/models.py")
    player.init_and_configure(model_paths=("app",), data_paths=["transitions"])
    assert player.make_migrations("legacy merge sources").returncode == 0
    assert player.migrate("--force").returncode == 0
    with sqlite3.connect(database) as connection:
        connection.executemany("INSERT INTO legacy_a VALUES (?, ?, ?, ?)", [
            (1, 10, 2, "first"), (2, 10, 3, "second"), (3, 20, 5, "twenty"),
        ])
        connection.executemany("INSERT INTO legacy_b VALUES (?, ?, ?, ?)", [
            (1, 10, 7, "other"), (2, 30, 11, "thirty"),
        ])
        connection.commit()
    player.write_model_source(MERGE_TARGET, filename="app/models.py")
    player.write_model_source(_merged_transition(_snapshot_id(tmp_path)), filename="transitions/consolidate.py")
    assert player.make_migrations("consolidate accounts", "--offline").returncode == 0
    plan_path = next(
        path for path in (tmp_path / "migrations" / "primary").glob("*.plan.json")
        if "data_spec" in json.loads(path.read_text(encoding="utf-8"))
    )
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert plan["data_spec"]["transitions"][0]["execution"]["size"] == 2
    assert any(step.get("batches") for step in plan["data_execution"]["upgrade"])
    rendered = player.cli.run("data", "render", "--format", "json")
    assert "many_to_one" in rendered.output
    docs = tmp_path / "data-docs"
    assert player.cli.run("data", "docs", "--output", str(docs)).returncode == 0
    assert any((docs / "transitions").glob("*.md"))
    assert player.migrate("--force").returncode == 0
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT id, total, name FROM accounts ORDER BY id").fetchall() == [
            (10, 12, "first"), (20, 5, "twenty"), (30, 11, "thirty"),
        ]
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name IN ('legacy_a', 'legacy_b')"
        ).fetchall() == []
        assert connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name LIKE '_dbwarden_merge_preserved_%'"
        ).fetchone()[0] == 2
    player.assert_converged()
    assert player.rollback().returncode == 0
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'accounts'"
        ).fetchall() == []
        assert connection.execute("SELECT COUNT(*) FROM legacy_a").fetchone()[0] == 3
        assert connection.execute("SELECT COUNT(*) FROM legacy_b").fetchone()[0] == 2
    assert player.migrate("--force", "--reapply-data").returncode == 0
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT id, total, name FROM accounts ORDER BY id").fetchall() == [
            (10, 12, "first"), (20, 5, "twenty"), (30, 11, "thirty"),
        ]


def test_sqlite_transition_preserves_source_and_round_trips(tmp_path: Path):
    player, database = _transition_project(tmp_path)
    with sqlite3.connect(database) as connection:
        connection.execute("INSERT INTO legacy VALUES (1, 'UY', 'Uruguay')")
        connection.commit()
    snapshot_id = _snapshot_id(tmp_path)
    player.write_model_source(COUNTRY_MODEL, filename="app/models.py")
    player.write_model_source(_transition(snapshot_id), filename="transitions/move.py")
    assert player.make_migrations("move legacy").returncode == 0
    plan_path = next(
        path
        for path in (tmp_path / "migrations" / "primary").glob("*.plan.json")
        if "data_spec" in json.loads(path.read_text(encoding="utf-8"))
    )
    original_plan = plan_path.read_text(encoding="utf-8")
    tampered = json.loads(original_plan)
    tampered["data_spec"]["transitions"][0]["identity"]["source_identity"] = ["code"]
    plan_path.write_text(json.dumps(tampered), encoding="utf-8")
    failed = player.cli.run("migrate", "--dry-run", "--data", check=False)
    assert failed.returncode != 0
    assert "untrusted data migration" in failed.output.lower()
    assert "malformed plan" in failed.output.lower()
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT id, code, name FROM legacy").fetchall() == [(1, "UY", "Uruguay")]
        assert connection.execute("SELECT code, name FROM countries").fetchall() == []
    plan_path.write_text(original_plan, encoding="utf-8")
    assert player.migrate("--force").returncode == 0
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT code, name FROM countries").fetchall() == [("UY", "Uruguay")]
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'legacy'"
        ).fetchall() == []
        preserved = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE '_dbwarden_preserved_%'"
        ).fetchall()
        assert len(preserved) == 1
    assert player.rollback().returncode == 0
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT id, code, name FROM legacy").fetchall() == [(1, "UY", "Uruguay")]
        assert connection.execute("SELECT code, name FROM countries").fetchall() == []
    assert player.migrate("--force", "--reapply-data").returncode == 0
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT code, name FROM countries").fetchall() == [("UY", "Uruguay")]
    player.assert_converged()


def test_sqlite_current_model_transition_keeps_source_and_round_trips(tmp_path: Path):
    database = tmp_path / "current-source.db"
    player = MigrationPlayer(f"sqlite:///{database}", tmp_path)
    player.write_model_source("", filename="app/__init__.py")
    player.write_model_source("", filename="transitions/__init__.py")
    player.write_model_source(CURRENT_SOURCE_MODEL, filename="app/models.py")
    player.init_and_configure(model_paths=("app",), data_paths=["transitions"])
    assert player.make_migrations("current source schema").returncode == 0
    assert player.migrate("--force").returncode == 0
    with sqlite3.connect(database) as connection:
        connection.execute("INSERT INTO legacy VALUES (1, 'Uruguay')")
        connection.commit()
    player.write_model_source(CURRENT_SOURCE_AND_TARGET_MODELS, filename="app/models.py")
    player.write_model_source(
        _current_source_transition(_snapshot_id(tmp_path)), filename="transitions/copy.py"
    )
    assert player.make_migrations("copy current source", "--offline").returncode == 0
    plan = next(
        json.loads(path.read_text(encoding="utf-8"))
        for path in (tmp_path / "migrations" / "primary").glob("*.plan.json")
        if "data_spec" in json.loads(path.read_text(encoding="utf-8"))
    )
    assert plan["data_spec"]["transitions"][0]["completion"]["policy"] == "keep"
    assert player.migrate("--force").returncode == 0
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT id, name FROM legacy").fetchall() == [(1, "Uruguay")]
        assert connection.execute("SELECT id, name FROM countries").fetchall() == [(1, "Uruguay")]
    assert player.cli.run("check", "--data").returncode == 0
    assert player.rollback().returncode == 0
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT id, name FROM legacy").fetchall() == [(1, "Uruguay")]
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='countries'"
        ).fetchall() == []
    assert player.migrate("--force", "--reapply-data").returncode == 0
    assert player.cli.run("check", "--data").returncode == 0


def test_sqlite_capture_transformation_round_trips_through_cli(tmp_path: Path):
    database = tmp_path / "capture.db"
    player = MigrationPlayer(f"sqlite:///{database}", tmp_path)
    player.write_model_source("", filename="app/__init__.py")
    player.write_model_source(CAPTURE_SOURCE_MODEL, filename="app/models.py")
    player.init_and_configure(model_paths=("app",))
    assert player.make_migrations("items schema").returncode == 0
    assert player.migrate("--force").returncode == 0
    with sqlite3.connect(database) as connection:
        connection.execute("INSERT INTO items VALUES (1, 7, 3)")
        connection.commit()
    player.write_model_source(CAPTURE_MODEL, filename="app/models.py")
    assert player.make_migrations("capture value", "--offline").returncode == 0
    assert player.migrate("--force").returncode == 0
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT value FROM items").fetchall() == [(8,)]
    assert player.cli.run("check", "--data").returncode == 0
    assert player.rollback().returncode == 0
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT value FROM items").fetchall() == [(3,)]
    assert player.migrate("--force", "--reapply-data").returncode == 0
    assert player.cli.run("check", "--data").returncode == 0


def test_sqlite_transition_target_conflict_fails_without_writes(tmp_path: Path):
    player, database = _transition_project(tmp_path)
    with sqlite3.connect(database) as connection:
        connection.execute("INSERT INTO legacy VALUES (1, 'UY', 'Uruguay')")
        connection.execute("INSERT INTO countries VALUES ('UY', 'Different')")
        connection.commit()
    player.write_model_source(COUNTRY_MODEL, filename="app/models.py")
    player.write_model_source(
        _transition(_snapshot_id(tmp_path), conflict="error"), filename="transitions/move.py"
    )
    assert player.make_migrations("conflicting move").returncode == 0
    failed = player.cli.run("migrate", "--force", check=False)
    assert failed.returncode != 0
    assert "conflict" in failed.output.lower()
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT id, code, name FROM legacy").fetchall() == [(1, "UY", "Uruguay")]
        assert connection.execute("SELECT code, name FROM countries").fetchall() == [("UY", "Different")]


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
