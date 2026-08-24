"""ClickHouse schema with TTL, codecs, and non-default engine settings coverage."""

from datetime import datetime
from typing import ClassVar

from dbwarden import ChEngineSpec, CHTableMeta
from dbwarden.databases.clickhouse import CHColumnMeta, ch
from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sensor_id: Mapped[str] = mapped_column(String(64), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    temp: Mapped[float] = mapped_column(Float, nullable=False)
    humidity: Mapped[float] = mapped_column(Float, nullable=False)

    class Meta(CHTableMeta):
        comment = "Sensor readings with TTL and codec coverage"
        ch_engine = ChEngineSpec("MergeTree")
        ch_order_by: ClassVar = ["sensor_id", "ts"]
        ch_ttl: ClassVar = ["ts + toIntervalMonth(6)"]
        ch_settings: ClassVar = {"index_granularity": "4096"}

        class temp(CHColumnMeta):
            ch = ch.field(codec="ZSTD(5)")

        class humidity(CHColumnMeta):
            ch = ch.field(ttl="ts + toIntervalDay(30)")
