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
    status: Mapped[SessionStatus] = mapped_column(Enum(SessionStatus), default=SessionStatus.queued)
    device_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    total_pairs: Mapped[int] = mapped_column(Integer, default=0)
    done_pairs: Mapped[int] = mapped_column(Integer, default=0)
    ok_pairs: Mapped[int] = mapped_column(Integer, default=0)
    fail_pairs: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
