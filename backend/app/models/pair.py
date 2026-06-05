from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index, String
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
