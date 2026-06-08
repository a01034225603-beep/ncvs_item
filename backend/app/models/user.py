"""
관리자 계정 ORM 모델 - users 테이블

역할:
  시스템 로그인 계정을 저장한다.
  비밀번호는 bcrypt 해시로 저장되며 평문은 절대 저장하지 않는다.
  초기 계정은 app/cli/seed.py 로 생성한다.
"""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
