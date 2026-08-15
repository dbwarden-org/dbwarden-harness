"""Reference ecommerce schema shared by round-trip and adoption suites."""

from typing import ClassVar

from dbwarden.databases import IndexSpec, TableMeta
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    orders: Mapped[list["Order"]] = relationship(back_populates="user")

    class Meta(TableMeta):
        comment = "Ecommerce users"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    user: Mapped[User] = relationship(back_populates="orders")

    class Meta(TableMeta):
        comment = "Ecommerce orders"
        indexes: ClassVar = [IndexSpec(name="ix_orders_user_id", columns=["user_id"])]


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    class Meta(TableMeta):
        comment = "Ecommerce order items"
