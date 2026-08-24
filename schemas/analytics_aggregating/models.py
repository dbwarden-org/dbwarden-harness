"""ClickHouse schema with an aggregating view for round-trip coverage."""

from datetime import datetime
from typing import ClassVar

from dbwarden import ChEngineSpec, CHTableMeta
from dbwarden.databases.clickhouse import AggregatingView, CHViewMeta, agg, aggregating_view
from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)

    class Meta(CHTableMeta):
        comment = "Analytics events"
        ch_engine = ChEngineSpec("MergeTree")
        ch_order_by: ClassVar = ["event_time", "id"]


class EventTypeStats(AggregatingView):
    __tablename__ = "event_type_stats"

    class Meta(CHViewMeta):
        ch = aggregating_view(
            source=Event,
            group_by=[Event.event_type],
            aggregates=[
                agg.sum(Event.amount).as_("total_amount"),
                agg.count().as_("event_count"),
            ],
            order_by=["event_type"],
        )
