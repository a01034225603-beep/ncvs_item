from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class HealthStatus(str, PyEnum):
    ok = "ok"
    fail = "fail"
    unknown = "unknown"


class DeviceHealth(Base):
    __tablename__ = "device_health"

    bacs_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("bacs_devices.id", ondelete="CASCADE"), primary_key=True
    )
    status: Mapped[HealthStatus] = mapped_column(Enum(HealthStatus), default=HealthStatus.unknown)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_ok_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_error: Mapped[str | None] = mapped_column(String(255))
    consecutive_fail: Mapped[int] = mapped_column(Integer, default=0)
