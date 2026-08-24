"""Declarative builders for disposable SQLAlchemy model modules.

The generative suites need to emit hundreds of small model files that differ in
exactly one property.  Hand-writing those as string literals hides the property
under test in a wall of boilerplate and makes it easy to write a case whose
"before" and "after" differ in more than one way.

These builders keep the varying property as the only visible argument.  Every
builder returns module source suitable for ``MigrationPlayer.write_model_source``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

GENERIC_IMPORTS = """\
import datetime, decimal, enum, uuid
from typing import Optional
from sqlalchemy import *
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from dbwarden.databases import TableMeta

Base = declarative_base()
"""

CLICKHOUSE_IMPORTS = """\
import datetime, decimal, enum, uuid
from typing import Optional
from sqlalchemy import (Column, Integer, BigInteger, SmallInteger, String, Text,
    Boolean, Float, Numeric, DateTime, Date, Time, LargeBinary, JSON, Enum,
    ForeignKey, UniqueConstraint, CheckConstraint, Index, text, func)
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from dbwarden.databases.clickhouse import *
from dbwarden.databases.clickhouse import ch, ch_table

Base = declarative_base()
"""

IMPORTS = {
    "clickhouse": CLICKHOUSE_IMPORTS,
    "sqlite": GENERIC_IMPORTS,
    "postgresql": GENERIC_IMPORTS,
    "mysql": GENERIC_IMPORTS,
    "mariadb": GENERIC_IMPORTS,
}


def module(backend: str, *bodies: str, preamble: str = "") -> str:
    """Assemble a model module for ``backend`` from class-definition bodies."""
    header = IMPORTS.get(backend, GENERIC_IMPORTS)
    return header + preamble + "\n" + "\n".join(bodies)


@dataclass(frozen=True)
class Column_:
    """One column in a generated model."""

    name: str
    type: str = "Integer"
    primary_key: bool = False
    args: str = ""

    def render(self) -> str:
        parts = [self.type]
        if self.primary_key:
            parts.append("primary_key=True")
        if self.args:
            parts.append(self.args)
        return f"    {self.name} = Column({', '.join(parts)})"


@dataclass(frozen=True)
class ClickHouseTable:
    """A ClickHouse model whose Meta is assembled from named properties.

    Every property defaults to "absent", so a matrix case that changes one
    property changes exactly one line of the emitted source.
    """

    name: str = "t"
    class_name: str = "T"
    columns: tuple[Column_, ...] = (Column_("id", primary_key=True), Column_("a"))
    engine: str = "merge_tree()"
    order_by: str | None = '["id"]'
    primary_key: str | None = None
    partition_by: str | None = None
    sample_by: str | None = None
    ttl: str | None = None
    settings: str | None = None
    indexes: str | None = None
    projections: str | None = None
    zookeeper_path: str | None = None
    replica_name: str | None = None
    comment: str | None = None
    column_meta: dict[str, str] = field(default_factory=dict)
    column_comments: dict[str, str] = field(default_factory=dict)
    base: str = "Base"
    meta_base: str = "CHTableMeta"
    raw_meta: str | None = None

    def _table_args(self) -> str:
        pairs = [
            ("engine", self.engine),
            ("order_by", self.order_by),
            ("primary_key", self.primary_key),
            ("partition_by", self.partition_by),
            ("sample_by", self.sample_by),
            ("ttl", self.ttl),
            ("settings", self.settings),
            ("projections", self.projections),
            ("indexes", self.indexes),
            ("zookeeper_path", self.zookeeper_path),
            ("replica_name", self.replica_name),
        ]
        return ", ".join(f"{key}={value}" for key, value in pairs if value is not None)

    def render(self) -> str:
        lines = [f"class {self.class_name}({self.base}):", f'    __tablename__ = "{self.name}"']
        lines += [column.render() for column in self.columns]
        lines.append("")
        lines.append(f"    class Meta({self.meta_base}):")
        if self.raw_meta is not None:
            lines.append(f"        {self.raw_meta}")
        else:
            lines.append(f"        ch = ch_table({self._table_args()})")
        if self.comment is not None:
            lines.append(f"        comment = {self.comment!r}")
        for column, spec in self.column_meta.items():
            lines.append(f"        class {column}(CHColumnMeta):")
            lines.append(f"            ch = ch.field({spec})")
        for column, text in self.column_comments.items():
            if column in self.column_meta:
                continue
            lines.append(f"        class {column}(CHColumnMeta):")
            lines.append(f"            comment = {text!r}")
        return "\n".join(lines) + "\n"

    def with_(self, **changes: Any) -> "ClickHouseTable":
        """Return a copy with the named properties replaced.

        This is the primitive the change matrix is built on: ``before`` and
        ``after`` differ only in what is passed here.
        """
        from dataclasses import replace

        return replace(self, **changes)

    def source(self) -> str:
        return module("clickhouse", self.render())


@dataclass(frozen=True)
class ClickHouseView:
    """A ClickHouse materialized/aggregating view model."""

    name: str = "v"
    class_name: str = "V"
    columns: tuple[Column_, ...] = (Column_("id", primary_key=True),)
    spec: str = 'materialized_view(select="SELECT id FROM src", engine=merge_tree(), order_by=["id"])'
    base: str = "Base"

    def render(self) -> str:
        lines = [f"class {self.class_name}({self.base}):", f'    __tablename__ = "{self.name}"']
        lines += [column.render() for column in self.columns]
        lines.append("")
        lines.append("    class Meta(CHViewMeta):")
        lines.append(f"        ch = {self.spec}")
        return "\n".join(lines) + "\n"


def clickhouse_single_column(column_type: str, *, column_meta: str | None = None) -> str:
    """A one-column ClickHouse table — the shape used by the type matrix."""
    table = ClickHouseTable(
        columns=(Column_("id", primary_key=True), Column_("c", column_type)),
        column_meta={"c": column_meta} if column_meta else {},
    )
    return table.source()
