"""
호출시험 세션 ORM 모델 - test_sessions 테이블

역할:
  한 번의 호출시험 실행 단위를 표현한다.
  상태 흐름: queued -> running -> completed / cancelled / failed
  total_pairs: 이 세션에서 실행할 전체 페어 수
  done_pairs, ok_pairs, fail_pairs: 실시간 진행 카운터
"""
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import JSON, BigInteger, DateTime, Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class SessionStatus(str, PyEnum):
    queued = "queued"
    running = "running"
    completed = "completed"
    cancelled = "cancelled"
    failed = "failed"


class TestSession(Base):
    __tablename__ = "test_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    # 시나리오 기반 시험일 경우 해당 시나리오 ID 저장 (NULL 허용 — 단독 세션 호환)
    scenario_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("scenarios.id"), nullable=True)
    status: Mapped[SessionStatus] = mapped_column(Enum(SessionStatus), default=SessionStatus.queued)
    device_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    total_pairs: Mapped[int] = mapped_column(Integer, default=0)
    done_pairs: Mapped[int] = mapped_column(Integer, default=0)
    ok_pairs: Mapped[int] = mapped_column(Integer, default=0)
    fail_pairs: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
