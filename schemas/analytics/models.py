"""Small analytics schema used by ClickHouse round-trip tests."""

from datetime import datetime
from typing import ClassVar

from dbwarden import ChEngineSpec, CHTableMeta
from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    event_name: Mapped[str] = mapped_column(String(120), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    class Meta(CHTableMeta):
        comment = "Analytics events"
        ch_engine = ChEngineSpec("MergeTree")
        ch_order_by: ClassVar = ["occurred_at", "id"]
