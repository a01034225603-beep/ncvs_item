"""
호출시험 시나리오 ORM 모델 - scenarios 테이블

역할:
  호출시험에서 사용할 발신(sender) 장비 목록과
  착신(receiver) 장비 목록의 조합을 이름을 붙여 저장한다.
  시나리오 실행 시 session_service 가 sender x receiver 페어를 생성한다.
"""
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy import BigInteger, DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Scenario(Base):
    """호출 시험 시나리오 — 발신/착신 장비 조합을 명명하여 저장."""

    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    # 발신 장비 ID 목록
    sender_device_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    # 착신 장비 ID 목록
    receiver_device_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=sa.text("now()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=sa.text("now()"),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
