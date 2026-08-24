"""Advanced PostgreSQL round-trip coverage for collation, compression, storage params, indexes, FKs, and checks."""

from typing import ClassVar

from dbwarden.databases import PgIndexSpec, check
from dbwarden.databases.pgsql import PGColumnMeta, PGTableMeta, pg
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    class Meta(PGTableMeta):
        comment = "PG advanced feature products"
        pg_storage_params: ClassVar = {"fillfactor": 80}

        class sku(PGColumnMeta):
            pg = pg.field(collation="C")

        class name(PGColumnMeta):
            pg = pg.field(compression="pglz")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", deferrable=True, initially="DEFERRED"),
        nullable=False,
    )
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    session_token: Mapped[str | None] = mapped_column(String(64), nullable=True)

    class Meta(PGTableMeta):
        comment = "PG advanced feature orders"
        pg_checks: ClassVar = [
            check("ck_orders_positive_id", "id > 0", no_inherit=True),
        ]
        pg_indexes: ClassVar = [
            PgIndexSpec(
                name="ix_orders_email_partial",
                columns=["email"],
                unique=True,
                where="email IS NOT NULL",
                nulls_not_distinct=True,
                include=["session_token"],
            ),
            PgIndexSpec(
                name="ix_orders_session_expr",
                columns=[],
                expression="lower(session_token)",
            ),
        ]
