"""
관리자 계정 리포지토리 - users 테이블

제공 함수:
  get_by_username() - 사용자명으로 계정 조회 (로그인 인증 시 사용)
  create()          - 새 계정 생성
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


async def get_by_username(session: AsyncSession, username: str) -> User | None:
    result = await session.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def create(session: AsyncSession, *, username: str, password_hash: str) -> User:
    obj = User(username=username, password_hash=password_hash)
    session.add(obj)
    await session.flush()
    return obj
