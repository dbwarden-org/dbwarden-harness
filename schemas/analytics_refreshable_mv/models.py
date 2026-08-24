"""ClickHouse schema with a refreshable materialized view for round-trip coverage."""

from datetime import datetime
from typing import ClassVar

from dbwarden import ChEngineSpec, CHTableMeta
from dbwarden.databases.clickhouse import CHViewMeta, MaterializedView, materialized_view
from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    event_name: Mapped[str] = mapped_column(String(120), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)

    class Meta(CHTableMeta):
        comment = "Analytics events"
        ch_engine = ChEngineSpec("MergeTree")
        ch_order_by: ClassVar = ["occurred_at", "id"]


class EventSummary(Base):
    __tablename__ = "event_summaries"

    event_name: Mapped[str] = mapped_column(String(120), primary_key=True)
    event_count: Mapped[int] = mapped_column(Integer)

    class Meta(CHTableMeta):
        ch_engine = ChEngineSpec("MergeTree")
        ch_order_by: ClassVar = ["event_name"]


class EventSummaryMV(MaterializedView):
    __tablename__ = "event_summaries_mv"

    class Meta(CHViewMeta):
        ch = materialized_view(
            select="SELECT event_name, count(id) AS event_count FROM events GROUP BY event_name",
            to="event_summaries",
            refresh="EVERY 1 HOUR",
        )
