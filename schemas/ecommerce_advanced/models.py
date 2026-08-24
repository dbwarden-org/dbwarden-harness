"""Advanced ecommerce schema for PostgreSQL round-trip coverage."""

from datetime import datetime
from typing import ClassVar

from dbwarden.databases import IndexSpec
from dbwarden.databases.pgsql import PGColumnMeta, PGTableMeta, pg
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    class Meta(PGTableMeta):
        comment = "Advanced ecommerce products"

        class id(PGColumnMeta):
            pg = pg.field(identity="always")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    class Meta(PGTableMeta):
        comment = "Advanced ecommerce orders"
        indexes: ClassVar = [
            IndexSpec(
                name="ix_orders_created_sort",
                columns=["quantity"],
                column_sorting={"quantity": "DESC NULLS LAST"},
            ),
        ]
