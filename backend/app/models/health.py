"""
DeviceHealth ORM 모델 - health_records 테이블

역할:
  BACS 장비별 UDP 헬스체크 결과를 저장한다.
  장비 1대당 1개 행이며 upsert 방식으로 갱신된다 (가장 최신 결과만 유지).
  status: online(응답 정상) / offline(타임아웃 또는 오류)
"""
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class HealthStatus(str, PyEnum):
    online  = "online"
    offline = "offline"
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
