"""
호출시험 페어 ORM 모델

역할:
  TestSessionPair: 세션 안 각 발신-착신 장비 쌍(1회 호출 단위)의 실행 상태 기록.
  PairLatestResult: 발신-착신 장비 쌍의 가장 최근 호출시험 결과 요약.
                   UI 결과 화면에서 최신 상태를 빠르게 보여주기 위해 사용한다.
"""
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class PairStatus(str, PyEnum):
    pending = "pending"
    running = "running"
    ok = "ok"
    fail = "fail"
    skipped = "skipped"


class PairLatestStatus(str, PyEnum):
    ok = "ok"
    fail = "fail"


class TestSessionPair(Base):
    __tablename__ = "test_session_pairs"
    __table_args__ = (
        Index("ix_session_status", "session_id", "status"),
        Index("ix_pair_src", "src_bacs_id"),
        Index("ix_pair_dst", "dst_bacs_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("test_sessions.id"))
    src_bacs_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("bacs_devices.id", ondelete="CASCADE"))
    dst_bacs_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("bacs_devices.id", ondelete="CASCADE"))
    # 라운드 번호 (1-based) — 같은 라운드 내 페어는 병렬, 다음 라운드는 이전 라운드 완료 후 시작
    round_number: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    status: Mapped[PairStatus] = mapped_column(Enum(PairStatus), default=PairStatus.pending)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    error_message: Mapped[str | None] = mapped_column(String(255))


class PairLatestResult(Base):
    __tablename__ = "pair_latest_result"

    src_bacs_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("bacs_devices.id", ondelete="CASCADE"), primary_key=True
    )
    dst_bacs_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("bacs_devices.id", ondelete="CASCADE"), primary_key=True
    )
    status: Mapped[PairLatestStatus] = mapped_column(Enum(PairLatestStatus), nullable=False)
    tested_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    session_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("test_sessions.id"))
    error_message: Mapped[str | None] = mapped_column(String(255))
