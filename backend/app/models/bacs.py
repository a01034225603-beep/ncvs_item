from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class BacsDevice(Base):
    __tablename__ = "bacs_devices"
    __table_args__ = (UniqueConstraint("ip_address", "udp_port", name="uq_bacs_ip_port"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    udp_port: Mapped[int] = mapped_column(Integer, default=7788)
    tcp_port: Mapped[int] = mapped_column(Integer, default=7788)
    location: Mapped[str | None] = mapped_column(String(255))
    sido: Mapped[str | None] = mapped_column(String(32))       # 시/도
    sigungu: Mapped[str | None] = mapped_column(String(64))    # 시/군/구
    geo_x: Mapped[float | None] = mapped_column(Float)         # 지도 X 좌표 (0~100%)
    geo_y: Mapped[float | None] = mapped_column(Float)         # 지도 Y 좌표 (0~100%)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # 포트별 전화번호 (0·1 = 발신TX, 2·3 = 착신RX) — 숫자+하이픈 허용, 예) 800-1200
    port0_phone: Mapped[str | None] = mapped_column(String(32))
    port1_phone: Mapped[str | None] = mapped_column(String(32))
    port2_phone: Mapped[str | None] = mapped_column(String(32))
    port3_phone: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
