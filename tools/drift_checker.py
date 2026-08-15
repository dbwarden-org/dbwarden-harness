from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, urlparse

from sqlalchemy import create_engine, inspect


@dataclass(frozen=True)
class SchemaSnapshot:
    tables: tuple[str, ...]
    columns: dict[str, tuple[str, ...]]
    indexes: dict[str, tuple[str, ...]]
    column_details: dict[str, tuple[tuple[str, str, bool, str | None], ...]] = field(default_factory=dict)
    primary_keys: dict[str, tuple[str, ...]] = field(default_factory=dict)
    foreign_keys: dict[str, tuple[tuple[str, str, str], ...]] = field(default_factory=dict)
    unique_constraints: dict[str, tuple[str, ...]] = field(default_factory=dict)
    views: tuple[str, ...] = ()
    table_options: dict[str, tuple[tuple[str, str], ...]] = field(default_factory=dict)


@dataclass(frozen=True)
class DriftItem:
    kind: str
    object_name: str
    expected: Any
    actual: Any


class DriftChecker:
    """Capture portable structural state through SQLAlchemy inspection."""

    def capture(self, database_url: str) -> SchemaSnapshot:
        if database_url.startswith(("http://", "https://")):
            return self._capture_clickhouse(database_url)

        engine = create_engine(database_url)
        try:
            inspector = inspect(engine)
            tables = tuple(sorted(inspector.get_table_names()))
            columns = {
                table: tuple(column["name"] for column in inspector.get_columns(table))
                for table in tables
            }
            column_details = {
                table: tuple(
                    (
                        column["name"],
                        str(column["type"]),
                        bool(column["nullable"]),
                        str(column["default"]) if column.get("default") is not None else None,
                    )
                    for column in inspector.get_columns(table)
                )
                for table in tables
            }
            indexes = {
                table: tuple(sorted(index["name"] for index in inspector.get_indexes(table) if index.get("name")))
                for table in tables
            }
            primary_keys = {
                table: tuple(inspector.get_pk_constraint(table).get("constrained_columns") or ())
                for table in tables
            }
            foreign_keys = {
                table: tuple(
                    sorted(
                        (
                            ",".join(key.get("constrained_columns") or ()),
                            key.get("referred_table", ""),
                            ",".join(key.get("referred_columns") or ()),
                        )
                        for key in inspector.get_foreign_keys(table)
                    )
                )
                for table in tables
            }
            unique_constraints = {
                table: tuple(
                    sorted(
                        constraint["name"]
                        for constraint in inspector.get_unique_constraints(table)
                        if constraint.get("name")
                    )
                )
                for table in tables
            }
            views = tuple(sorted(inspector.get_view_names()))
            table_options = {}
            for table in tables:
                try:
                    options = inspector.get_table_options(table)
                except NotImplementedError:
                    options = {}
                table_options[table] = tuple(sorted((str(key), str(value)) for key, value in options.items()))
            return SchemaSnapshot(
                tables,
                columns,
                indexes,
                column_details,
                primary_keys,
                foreign_keys,
                unique_constraints,
                views,
                table_options,
            )
        finally:
            engine.dispose()

    def _capture_clickhouse(self, database_url: str) -> SchemaSnapshot:
        import clickhouse_connect

        parsed = urlparse(database_url)
        query = parse_qs(parsed.query)
        client = clickhouse_connect.get_client(
            host=parsed.hostname or "localhost",
            port=parsed.port or 8123,
            username=parsed.username or "default",
            password=parsed.password or "",
            database=parsed.path.lstrip("/") or "default",
            secure=parsed.scheme == "https",
            **{key: values[-1] for key, values in query.items()},
        )
        try:
            database = parsed.path.lstrip("/") or "default"
            tables = tuple(
                row[0]
                for row in client.query(
                    "SELECT name FROM system.tables WHERE database = %(database)s AND is_temporary = 0 "
                    "ORDER BY name",
                    parameters={"database": database},
                ).result_rows
            )
            table_rows = client.query(
                "SELECT name, engine, sorting_key, partition_key, "
                "primary_key FROM system.tables "
                "WHERE database = %(database)s AND is_temporary = 0 ORDER BY name",
                parameters={"database": database},
            ).result_rows
            column_rows = client.query(
                "SELECT table, name, type, default_kind, default_expression, is_in_partition_key "
                "FROM system.columns WHERE database = %(database)s ORDER BY table, position",
                parameters={"database": database},
            ).result_rows
            grouped: dict[str, list[tuple[str, str, bool, str | None]]] = {table: [] for table in tables}
            for table, name, type_name, default_kind, default_expression, _ in column_rows:
                grouped.setdefault(table, []).append(
                    (
                        name,
                        type_name,
                        False,
                        default_expression if default_kind else None,
                    )
                )
            return SchemaSnapshot(
                tables=tables,
                columns={table: tuple(item[0] for item in grouped[table]) for table in tables},
                indexes={table: () for table in tables},
                column_details={table: tuple(grouped[table]) for table in tables},
                primary_keys={table: () for table in tables},
                foreign_keys={table: () for table in tables},
                unique_constraints={table: () for table in tables},
                table_options={
                    table: tuple(
                        (key, str(value))
                        for key, value in zip(
                            ("engine", "sorting_key", "partition_key", "primary_key"),
                            row[1:],
                        )
                    )
                    for row in table_rows
                    for table in (row[0],)
                },
            )
        finally:
            client.close()

    def diff(self, expected: SchemaSnapshot, actual: SchemaSnapshot) -> list[DriftItem]:
        items: list[DriftItem] = []
        if expected.tables != actual.tables:
            items.append(DriftItem("tables", "__all__", expected.tables, actual.tables))
        if expected.views != actual.views:
            items.append(DriftItem("views", "__all__", expected.views, actual.views))
        for table in sorted(set(expected.columns) | set(actual.columns)):
            if expected.columns.get(table) != actual.columns.get(table):
                items.append(DriftItem("columns", table, expected.columns.get(table), actual.columns.get(table)))
            if expected.indexes.get(table) != actual.indexes.get(table):
                items.append(DriftItem("indexes", table, expected.indexes.get(table), actual.indexes.get(table)))
            if expected.column_details.get(table) != actual.column_details.get(table):
                items.append(
                    DriftItem(
                        "column_details",
                        table,
                        expected.column_details.get(table),
                        actual.column_details.get(table),
                    )
                )
            if expected.primary_keys.get(table) != actual.primary_keys.get(table):
                items.append(
                    DriftItem("primary_keys", table, expected.primary_keys.get(table), actual.primary_keys.get(table))
                )
            if expected.foreign_keys.get(table) != actual.foreign_keys.get(table):
                items.append(
                    DriftItem("foreign_keys", table, expected.foreign_keys.get(table), actual.foreign_keys.get(table))
                )
            if expected.unique_constraints.get(table) != actual.unique_constraints.get(table):
                items.append(
                    DriftItem(
                        "unique_constraints",
                        table,
                        expected.unique_constraints.get(table),
                        actual.unique_constraints.get(table),
                    )
                )
            if expected.table_options.get(table) != actual.table_options.get(table):
                items.append(
                    DriftItem(
                        "table_options",
                        table,
                        expected.table_options.get(table),
                        actual.table_options.get(table),
                    )
                )
        return items

    def assert_equal(self, expected: SchemaSnapshot, actual: SchemaSnapshot) -> None:
        drift = self.diff(expected, actual)
        if drift:
            details = "\n".join(f"{item.kind}:{item.object_name}" for item in drift)
            raise AssertionError(f"Schema drift detected:\n{details}")
