"""PostgreSQL feature coverage for generated columns, identity params, and exclusion constraints."""

from typing import ClassVar

from dbwarden.databases.pgsql import PGColumnMeta, PGTableMeta, pg
from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_ref: Mapped[str] = mapped_column(String(32), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False)
    total_amount: Mapped[int] = mapped_column(Integer, nullable=False)

    class Meta(PGTableMeta):
        comment = "PG feature coverage orders"

        class id(PGColumnMeta):
            pg = pg.field(
                identity="always",
                identity_start=1000,
                identity_increment=5,
                identity_min=1,
                identity_max=1000000,
            )

        class total_amount(PGColumnMeta):
            pg = pg.field(generated="quantity * unit_price")

        pg_excludes: ClassVar = [
            {
                "name": "no_duplicate_order_ref",
                "expression": "EXCLUDE USING btree (order_ref WITH =)",
            },
        ]
