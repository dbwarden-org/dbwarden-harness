"""ClickHouse schema with projections and skip indexes for round-trip coverage."""

from datetime import datetime
from typing import ClassVar

from dbwarden import ChEngineSpec, CHTableMeta
from dbwarden.databases.clickhouse import ChIndexSpec, ProjectionSpec
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
        ch_engine = ChEngineSpec("MergeTree")
        ch_order_by: ClassVar = ["occurred_at", "id"]
        ch_projections: ClassVar = [
            ProjectionSpec(
                name="by_name",
                query="SELECT event_name, count() GROUP BY event_name",
            ),
        ]
        ch_indexes: ClassVar = [
            ChIndexSpec(
                name="ix_event_name",
                columns=["event_name"],
                type="bloom_filter",
                granularity=1,
            ),
        ]
