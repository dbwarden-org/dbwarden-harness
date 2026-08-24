"""ClickHouse schema with a materialized view that JOINs multiple source tables."""

from typing import ClassVar

from dbwarden import ChEngineSpec, CHTableMeta
from dbwarden.databases.clickhouse import CHViewMeta, MaterializedView, materialized_view
from sqlalchemy import Integer, String, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    value: Mapped[int] = mapped_column(Integer, nullable=False)

    class Meta(CHTableMeta):
        ch_engine = ChEngineSpec("MergeTree")
        ch_order_by: ClassVar = ["id"]


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)

    class Meta(CHTableMeta):
        ch_engine = ChEngineSpec("MergeTree")
        ch_order_by: ClassVar = ["id"]


class EventUserValue(MaterializedView):
    __tablename__ = "event_user_values"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[int] = mapped_column(Integer, nullable=False)

    class Meta(CHViewMeta):
        ch = materialized_view(
            select=select(Event.id, User.name, Event.value).where(Event.user_id == User.id),
            engine=ChEngineSpec("MergeTree"),
            order_by=["id"],
        )
