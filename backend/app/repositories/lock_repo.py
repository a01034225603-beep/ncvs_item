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
