from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class DeviceLock(Base):
    __tablename__ = "device_locks"

    bacs_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("bacs_devices.id"), primary_key=True
    )
    session_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("test_sessions.id"))
    acquired_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
