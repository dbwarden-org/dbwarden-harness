"""ClickHouse schema exercising native types that need round-trip coverage."""

import enum
from datetime import datetime
from typing import ClassVar
from uuid import UUID

from dbwarden import ChEngineSpec, CHTableMeta
from dbwarden.databases.clickhouse import CHColumnMeta, ch
from sqlalchemy import DateTime, Enum, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Status(enum.Enum):
    pending = "pending"
    done = "done"


class TypedEvent(Base):
    __tablename__ = "typed_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(Enum(Status), nullable=False)
    fixed_code: Mapped[str] = mapped_column(String(16), nullable=False)
    upload_id: Mapped[UUID] = mapped_column(PGUUID, nullable=False)

    class Meta(CHTableMeta):
        ch_engine = ChEngineSpec("MergeTree")
        ch_order_by: ClassVar = ["id"]

        class fixed_code(CHColumnMeta):
            ch = ch.field(type="FixedString(16)")
