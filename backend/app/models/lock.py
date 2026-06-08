"""
Device Lock ORM 모델 - device_locks 테이블

역할:
  호출시험 실행 중 특정 BACS 장비가 '사용 중'임을 DB에 표시하는 잠금 테이블.
  실제 동시성 제어는 인메모리 DeviceLocker(asyncio.Lock)가 담당하고,
  이 테이블은 재시작/장애 후 잠금 상태 복원 및 UI 활성 잠금 표시에 사용한다.
  (main.py startup 시 lock_repo.clear_all() 호출로 자동 초기화)
"""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class DeviceLock(Base):
    """BACS 장비 1대당 1개 행 - 페어 실행 중 잠금 상태를 표시."""
    __tablename__ = "device_locks"

    # bacs_id: 잠긴 장비 ID (기본키 - 동일 장비가 동시에 두 페어에 사용 불가 보장)
    bacs_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("bacs_devices.id", ondelete="CASCADE"), primary_key=True
    )
    # session_id: 어떤 세션이 이 장비를 잠갔는지 추적
    session_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("test_sessions.id"))
    # acquired_at: 잠금 획득 시각 (디버깅/모니터링 용도)
    acquired_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
