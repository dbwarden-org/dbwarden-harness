"""Identifiers and nullable/default values that exercise SQL quoting."""

from dbwarden.databases import TableMeta
from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ReservedKeyword(Base):
    __tablename__ = "reserved_keywords"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order: Mapped[str] = mapped_column("order", String(80), nullable=False)
    select: Mapped[bool] = mapped_column("select", Boolean, nullable=False, default=False)
    optional_note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    class Meta(TableMeta):
        comment = "Reserved keyword identifiers"
