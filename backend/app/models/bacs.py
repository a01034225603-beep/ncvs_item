from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class BacsDevice(Base):
    __tablename__ = "bacs_devices"
    __table_args__ = (UniqueConstraint("ip_address", "udp_port", name="uq_bacs_ip_port"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    node_id: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    udp_port: Mapped[int] = mapped_column(Integer, default=7788)
    tcp_port: Mapped[int] = mapped_column(Integer, default=7788)
    location: Mapped[str | None] = mapped_column(String(255))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
