"""
Device Lock 리포지토리 - device_locks 테이블

제공 함수:
  add()       - 장비 잠금 레코드 추가 (호출시험 페어 시작 시)
  remove()    - 장비 잠금 해제 (호출시험 페어 완료 시)
  clear_all() - 전체 잠금 초기화 (서버 재시작 시 cleanup)
"""
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DeviceLock


async def add(session: AsyncSession, bacs_id: int, session_id: int) -> None:
    session.add(DeviceLock(bacs_id=bacs_id, session_id=session_id))
    await session.flush()


async def remove(session: AsyncSession, bacs_id: int) -> None:
    await session.execute(delete(DeviceLock).where(DeviceLock.bacs_id == bacs_id))
    await session.flush()


async def clear_all(session: AsyncSession) -> None:
    await session.execute(delete(DeviceLock))
    await session.flush()
