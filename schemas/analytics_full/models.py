"""Full-featured analytics schema for ClickHouse round-trip coverage."""

from datetime import datetime
from typing import ClassVar

from dbwarden import ChEngineSpec, CHTableMeta
from dbwarden.databases.clickhouse import (
    CHViewMeta,
    MaterializedView,
    materialized_view,
)
from sqlalchemy import DateTime, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    event_name: Mapped[str] = mapped_column(nullable=False)
    user_id: Mapped[int] = mapped_column(nullable=False)
    value: Mapped[float] = mapped_column(default=0.0)
    event_type: Mapped[str] = mapped_column(nullable=False)

    class Meta(CHTableMeta):
        comment = "Analytics events"
        ch_engine = ChEngineSpec("MergeTree")
        ch_order_by: ClassVar = ["occurred_at", "id"]


class EventTypeStat(MaterializedView):
    __tablename__ = "event_type_stats"

    event_type: Mapped[str] = mapped_column(primary_key=True)
    event_count: Mapped[int] = mapped_column()

    class Meta(CHViewMeta):
        ch = materialized_view(
            select=select(Event.event_type, func.count(Event.id).label("event_count")).group_by(Event.event_type),
            engine=ChEngineSpec("MergeTree"),
            order_by=["event_type"],
        )
