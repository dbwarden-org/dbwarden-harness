"""Accounts and audit records used by PostgreSQL plugin suites."""

from datetime import datetime
from typing import ClassVar

from dbwarden.databases import IndexSpec, TableMeta
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    audit_events: Mapped[list["AuditEvent"]] = relationship(back_populates="account")

    class Meta(TableMeta):
        comment = "RBAC accounts"


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    account: Mapped[Account] = relationship(back_populates="audit_events")

    class Meta(TableMeta):
        comment = "RBAC audit events"
        indexes: ClassVar = [IndexSpec(name="ix_audit_events_account_id", columns=["account_id"])]
