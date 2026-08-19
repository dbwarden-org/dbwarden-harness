from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from infrastructure.providers import provider_for
from tools.drift_checker import DriftChecker
from tools.migration_player import MigrationPlayer


def _write_migration(directory: Path, number: int, upgrade: str, rollback: str) -> None:
    (directory / f"primary__{number:04d}_adversarial.sql").write_text(
        f"-- upgrade\n{upgrade}\n-- rollback\n{rollback}\n",
        encoding="utf-8",
    )


def _pg_query(database_url: str, statement: str, params: dict | None = None):
    engine = create_engine(database_url)
    try:
        with engine.connect() as conn:
            return conn.execute(text(statement), params or {}).fetchall()
    finally:
        engine.dispose()


def _pg_execute(database_url: str, statement: str, params: dict | None = None) -> None:
    engine = create_engine(database_url)
    try:
        with engine.begin() as conn:
            conn.execute(text(statement), params or {})
    finally:
        engine.dispose()


def _column_type(snapshot, table: str, column: str) -> str | None:
    for name, type_name, *_ in snapshot.column_details.get(table, ()):
        if name == column:
            return type_name
    return None


def _has_rename_operations(operations: list[dict]) -> bool:
    for operation in operations:
        op_type = operation.get("operation", "").lower()
        if op_type == "rename_column":
            return True
        if op_type == "alter_column" and operation.get("new_column_name"):
            return True
    return False


@pytest.mark.integration
def test_rename_and_type_change_simultaneously(tmp_path: Path):
    provider = provider_for("postgres", "17")
    try:
        player = MigrationPlayer(provider.start(), tmp_path)
        player.init_and_configure(database_type="postgresql")
        migration_dir = tmp_path / "migrations" / "primary"
        migration_dir.mkdir(parents=True, exist_ok=True)
        _write_migration(
            migration_dir,
            1,
            "CREATE TABLE accounts (id INTEGER PRIMARY KEY, old_name VARCHAR(50));",
            "DROP TABLE accounts;",
        )
        _write_migration(
            migration_dir,
            2,
            "ALTER TABLE accounts RENAME COLUMN old_name TO new_name; "
            "ALTER TABLE accounts ALTER COLUMN new_name TYPE TEXT;",
            "ALTER TABLE accounts ALTER COLUMN new_name TYPE VARCHAR(50); "
            "ALTER TABLE accounts RENAME COLUMN new_name TO old_name;",
        )

        assert player.migrate().returncode == 0
        snapshot = DriftChecker().capture(player.database_url)
        assert _column_type(snapshot, "accounts", "new_name") == "TEXT"
        assert "old_name" not in snapshot.columns["accounts"]

        assert player.rollback().returncode == 0
        snapshot = DriftChecker().capture(player.database_url)
        assert _column_type(snapshot, "accounts", "old_name") == "VARCHAR(50)"
        assert "new_name" not in snapshot.columns["accounts"]
    finally:
        provider.stop()


@pytest.mark.integration
def test_rename_and_constraint_change(tmp_path: Path):
    provider = provider_for("postgres", "17")
    try:
        player = MigrationPlayer(provider.start(), tmp_path)
        player.init_and_configure(database_type="postgresql")
        migration_dir = tmp_path / "migrations" / "primary"
        migration_dir.mkdir(parents=True, exist_ok=True)
        _write_migration(
            migration_dir,
            1,
            "CREATE TABLE widgets (id INTEGER PRIMARY KEY, code TEXT);",
            "DROP TABLE widgets;",
        )
        _write_migration(
            migration_dir,
            2,
            "ALTER TABLE widgets RENAME COLUMN code TO sku; "
            "ALTER TABLE widgets ADD CONSTRAINT chk_sku CHECK (sku ~ '^[A-Z]{3}');",
            "ALTER TABLE widgets DROP CONSTRAINT chk_sku; "
            "ALTER TABLE widgets RENAME COLUMN sku TO code;",
        )

        assert player.migrate().returncode == 0
        snapshot = DriftChecker().capture(player.database_url)
        assert "sku" in snapshot.columns["widgets"]
        assert "code" not in snapshot.columns["widgets"]

        constraint = _pg_query(
            player.database_url,
            "SELECT conname FROM pg_constraint WHERE conrelid = 'widgets'::regclass "
            "AND contype = 'c' AND conname = 'chk_sku'",
        )
        assert constraint, "CHECK constraint chk_sku was not created"

        with pytest.raises(DBAPIError):
            _pg_execute(player.database_url, "INSERT INTO widgets (id, sku) VALUES (1, 'low');")

        assert player.rollback().returncode == 0
        snapshot = DriftChecker().capture(player.database_url)
        assert "code" in snapshot.columns["widgets"]
        assert "sku" not in snapshot.columns["widgets"]
        constraint = _pg_query(
            player.database_url,
            "SELECT conname FROM pg_constraint WHERE conrelid = 'widgets'::regclass "
            "AND contype = 'c' AND conname = 'chk_sku'",
        )
        assert not constraint, "CHECK constraint chk_sku was not dropped on rollback"
    finally:
        provider.stop()


@pytest.mark.integration
def test_drop_and_recreate_same_signature(tmp_path: Path):
    provider = provider_for("postgres", "17")
    try:
        player = MigrationPlayer(provider.start(), tmp_path)
        player.init_and_configure(database_type="postgresql")
        migration_dir = tmp_path / "migrations" / "primary"
        migration_dir.mkdir(parents=True, exist_ok=True)
        _write_migration(
            migration_dir,
            1,
            "CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT); "
            "INSERT INTO items (id, name) VALUES (1, 'first');",
            "DROP TABLE items;",
        )
        _write_migration(
            migration_dir,
            2,
            "DROP TABLE IF EXISTS items; CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT);",
            "DROP TABLE IF EXISTS items; CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT);",
        )

        assert player.migrate().returncode == 0
        after_recreate = DriftChecker().capture(player.database_url)
        assert "items" in after_recreate.tables

        assert player.rollback().returncode == 0
        assert player.migrate().returncode == 0
        after_second_migrate = DriftChecker().capture(player.database_url)

        # Structural signature is identical, but data is gone (destructive operation).
        DriftChecker().assert_equal(after_recreate, after_second_migrate)
        player.assert_history_integrity()

        rows = _pg_query(player.database_url, "SELECT COUNT(*) FROM items")
        assert rows[0][0] == 0, "Recreated table retained rows from the dropped table"
    finally:
        provider.stop()


@pytest.mark.integration
def test_ambiguous_rename(tmp_path: Path):
    """Adversarial rename detection and SQL contract for column replacement."""
    provider = provider_for("postgres", "17")
    try:
        url = provider.start()

        # Phase 1: SQL contract. Manually simulate an ambiguous rename by dropping
        # two columns and adding two new columns without using RENAME COLUMN.
        sql_contract_dir = tmp_path / "sql_contract"
        sql_contract_dir.mkdir(parents=True, exist_ok=True)
        player = MigrationPlayer(url, sql_contract_dir)
        player.init_and_configure(database_type="postgresql")
        migration_dir = player.work_dir / "migrations" / "primary"
        migration_dir.mkdir(parents=True, exist_ok=True)
        _write_migration(
            migration_dir,
            1,
            "CREATE TABLE widgets (id INTEGER PRIMARY KEY, a1 VARCHAR(50) NOT NULL, "
            "a2 VARCHAR(50) NOT NULL);",
            "DROP TABLE widgets;",
        )
        _write_migration(
            migration_dir,
            2,
            "ALTER TABLE widgets DROP COLUMN a1; ALTER TABLE widgets DROP COLUMN a2; "
            "ALTER TABLE widgets ADD COLUMN b1 VARCHAR(50) NOT NULL DEFAULT ''; "
            "ALTER TABLE widgets ADD COLUMN b2 VARCHAR(50) NOT NULL DEFAULT '';",
            "ALTER TABLE widgets DROP COLUMN b1; ALTER TABLE widgets DROP COLUMN b2; "
            "ALTER TABLE widgets ADD COLUMN a1 VARCHAR(50) NOT NULL DEFAULT ''; "
            "ALTER TABLE widgets ADD COLUMN a2 VARCHAR(50) NOT NULL DEFAULT '';",
        )

        assert player.migrate().returncode == 0
        snapshot = DriftChecker().capture(player.database_url)
        assert "b1" in snapshot.columns["widgets"]
        assert "b2" in snapshot.columns["widgets"]
        assert "a1" not in snapshot.columns["widgets"]
        assert "a2" not in snapshot.columns["widgets"]

        assert player.rollback().returncode == 0
        snapshot = DriftChecker().capture(player.database_url)
        assert "a1" in snapshot.columns["widgets"]
        assert "a2" in snapshot.columns["widgets"]
        assert "b1" not in snapshot.columns["widgets"]
        assert "b2" not in snapshot.columns["widgets"]

        # Phase 2: make-migrations must not silently emit an incorrect rename chain
        # when two columns are replaced by two new columns with no clear mapping.
        provider.reset()
        model_diff_dir = tmp_path / "model_diff"
        model_diff_dir.mkdir(parents=True, exist_ok=True)
        model_player = MigrationPlayer(url, model_diff_dir)
        model_player.init_and_configure(database_type="postgresql", model_paths=("app",))
        model_player.write_model_source("", filename="app/__init__.py")
        model_player.write_model_source(
            '''\
from dbwarden.databases import TableMeta
from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Widget(Base):
    __tablename__ = "widgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    a1: Mapped[str] = mapped_column(String(50), nullable=False)
    a2: Mapped[str] = mapped_column(String(50), nullable=False)

    class Meta(TableMeta):
        comment = "Widget v1"
''',
            filename="app/models.py",
        )
        assert model_player.make_migrations("v1").returncode == 0
        assert model_player.migrate().returncode == 0

        model_player.write_model_source(
            '''\
from dbwarden.databases import TableMeta
from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Widget(Base):
    __tablename__ = "widgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    b1: Mapped[str] = mapped_column(String(50), nullable=False)
    b2: Mapped[str] = mapped_column(String(50), nullable=False)

    class Meta(TableMeta):
        comment = "Widget v2"
''',
            filename="app/models.py",
        )
        result = model_player.cli.run("make-migrations", "v2", check=False)
        if result.returncode == 0:
            operations = model_player.diff_operations()
            assert not _has_rename_operations(
                operations
            ), "make-migrations silently emitted an unsafe rename chain for an ambiguous rename"
    finally:
        provider.stop()


@pytest.mark.integration
def test_partition_changes(tmp_path: Path):
    provider = provider_for("postgres", "17")
    try:
        player = MigrationPlayer(provider.start(), tmp_path)
        player.init_and_configure(database_type="postgresql")
        migration_dir = tmp_path / "migrations" / "primary"
        migration_dir.mkdir(parents=True, exist_ok=True)
        _write_migration(
            migration_dir,
            1,
            "CREATE TABLE measurements ("
            "id INTEGER NOT NULL, measured_at TIMESTAMP NOT NULL, value NUMERIC, "
            "PRIMARY KEY (id, measured_at)"
            ") PARTITION BY RANGE (measured_at);",
            "DROP TABLE measurements;",
        )
        _write_migration(
            migration_dir,
            2,
            "CREATE TABLE measurements_2024 PARTITION OF measurements "
            "FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');",
            "DROP TABLE measurements_2024;",
        )

        assert player.migrate().returncode == 0
        partitions = _pg_query(
            player.database_url,
            "SELECT inhrelid::regclass::text FROM pg_inherits "
            "WHERE inhparent = 'measurements'::regclass",
        )
        partition_names = {row[0] for row in partitions}
        assert "measurements_2024" in partition_names

        _pg_execute(
            player.database_url,
            "INSERT INTO measurements (id, measured_at, value) VALUES (1, '2024-06-01', 42);",
        )
        routed = _pg_query(
            player.database_url,
            "SELECT tableoid::regclass::text FROM measurements WHERE id = 1",
        )
        assert routed[0][0] == "measurements_2024"

        assert player.rollback().returncode == 0
        partitions = _pg_query(
            player.database_url,
            "SELECT inhrelid::regclass::text FROM pg_inherits "
            "WHERE inhparent = 'measurements'::regclass",
        )
        assert not partitions
    finally:
        provider.stop()


@pytest.mark.integration
def test_generated_columns(tmp_path: Path):
    provider = provider_for("postgres", "17")
    try:
        player = MigrationPlayer(provider.start(), tmp_path)
        player.init_and_configure(database_type="postgresql")
        migration_dir = tmp_path / "migrations" / "primary"
        migration_dir.mkdir(parents=True, exist_ok=True)
        _write_migration(
            migration_dir,
            1,
            "CREATE TABLE invoices (id INTEGER PRIMARY KEY, qty INTEGER, price NUMERIC);",
            "DROP TABLE invoices;",
        )
        _write_migration(
            migration_dir,
            2,
            "ALTER TABLE invoices ADD COLUMN total INTEGER "
            "GENERATED ALWAYS AS (qty * price) STORED;",
            "ALTER TABLE invoices DROP COLUMN total;",
        )

        assert player.migrate().returncode == 0
        expression = _pg_query(
            player.database_url,
            "SELECT pg_get_expr(d.adbin, d.adrelid) FROM pg_attrdef d "
            "JOIN pg_attribute a ON a.attrelid = d.adrelid AND a.attnum = d.adnum "
            "WHERE a.attrelid = 'invoices'::regclass AND a.attname = 'total'",
        )
        assert expression, "Generated column definition not found in pg_attrdef"
        assert "qty" in expression[0][0] and "price" in expression[0][0]

        _pg_execute(
            player.database_url,
            "INSERT INTO invoices (id, qty, price) VALUES (1, 3, 10);",
        )
        rows = _pg_query(player.database_url, "SELECT total FROM invoices WHERE id = 1")
        assert rows[0][0] == 30

        assert player.rollback().returncode == 0
        snapshot = DriftChecker().capture(player.database_url)
        assert "total" not in snapshot.columns["invoices"]
    finally:
        provider.stop()


@pytest.mark.integration
def test_concurrent_index(tmp_path: Path):
    provider = provider_for("postgres", "17")
    try:
        player = MigrationPlayer(provider.start(), tmp_path)
        player.init_and_configure(database_type="postgresql")
        migration_dir = tmp_path / "migrations" / "primary"
        migration_dir.mkdir(parents=True, exist_ok=True)
        _write_migration(
            migration_dir,
            1,
            "CREATE TABLE accounts (id INTEGER PRIMARY KEY, name TEXT);",
            "DROP TABLE accounts;",
        )
        _write_migration(
            migration_dir,
            2,
            "CREATE INDEX CONCURRENTLY idx_accounts_name ON accounts(name);",
            "DROP INDEX idx_accounts_name;",
        )

        # Use check=False because CONCURRENTLY may fail if dbwarden wraps the
        # migration in a transaction. The strict contract requires a clear outcome.
        result = player.cli.run("migrate", check=False)

        if result.returncode != 0:
            # PostgreSQL refuses CREATE INDEX CONCURRENTLY inside a transaction.
            # dbwarden must report a clear error and not mark the migration applied.
            assert "concurrently" in result.output.lower(), result.output
            status = player.status()
            assert "0002" not in status.plain_output or "pending" in status.plain_output.lower()
        else:
            indexes = _pg_query(
                player.database_url,
                "SELECT indexname FROM pg_indexes WHERE tablename = 'accounts' "
                "AND indexname = 'idx_accounts_name'",
            )
            assert indexes, "CONCURRENTLY migration succeeded but index does not exist"
    finally:
        provider.stop()


@pytest.mark.integration
def test_enum_changes(tmp_path: Path):
    provider = provider_for("postgres", "17")
    try:
        player = MigrationPlayer(provider.start(), tmp_path)
        player.init_and_configure(database_type="postgresql")
        migration_dir = tmp_path / "migrations" / "primary"
        migration_dir.mkdir(parents=True, exist_ok=True)
        _write_migration(
            migration_dir,
            1,
            "CREATE TYPE status_enum AS ENUM ('new', 'active'); "
            "CREATE TABLE jobs (id INTEGER PRIMARY KEY, status status_enum NOT NULL);",
            "DROP TABLE jobs; DROP TYPE status_enum;",
        )
        _write_migration(
            migration_dir,
            2,
            "ALTER TYPE status_enum ADD VALUE 'archived';",
            "ALTER TABLE jobs DROP COLUMN status; DROP TYPE status_enum; "
            "CREATE TYPE status_enum AS ENUM ('new', 'active'); "
            "ALTER TABLE jobs ADD COLUMN status status_enum NOT NULL DEFAULT 'new';",
        )

        assert player.migrate().returncode == 0
        labels = _pg_query(
            player.database_url,
            "SELECT enumlabel FROM pg_enum WHERE enumtypid = 'status_enum'::regtype "
            "ORDER BY enumsortorder",
        )
        assert [row[0] for row in labels] == ["new", "active", "archived"]

        _pg_execute(
            player.database_url,
            "INSERT INTO jobs (id, status) VALUES (1, 'archived');",
        )
        rows = _pg_query(player.database_url, "SELECT status FROM jobs WHERE id = 1")
        assert rows[0][0] == "archived"

        assert player.rollback().returncode == 0
        labels = _pg_query(
            player.database_url,
            "SELECT enumlabel FROM pg_enum WHERE enumtypid = 'status_enum'::regtype "
            "ORDER BY enumsortorder",
        )
        assert [row[0] for row in labels] == ["new", "active"]
    finally:
        provider.stop()
