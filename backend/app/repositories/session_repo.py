from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SessionStatus, TestSession


async def create(
    session: AsyncSession, *, user_id: int, device_ids: list[int], total_pairs: int
) -> TestSession:
    obj = TestSession(
        user_id=user_id,
        device_ids=device_ids,
        total_pairs=total_pairs,
        status=SessionStatus.queued,
        started_at=datetime.utcnow(),
    )
    session.add(obj)
    await session.flush()
    return obj


async def get(session: AsyncSession, session_id: int) -> TestSession | None:
    return await session.get(TestSession, session_id)


async def list_active(session: AsyncSession) -> list[TestSession]:
    result = await session.execute(
        select(TestSession).where(
            TestSession.status.in_([SessionStatus.queued, SessionStatus.running])
        )
    )
    return list(result.scalars().all())


async def mark_running(session: AsyncSession, session_id: int) -> None:
    obj = await session.get(TestSession, session_id)
    if obj is not None:
        obj.status = SessionStatus.running


async def mark_finished(
    session: AsyncSession, session_id: int, status: SessionStatus
) -> None:
    obj = await session.get(TestSession, session_id)
    if obj is not None:
        obj.status = status
        obj.finished_at = datetime.utcnow()


async def increment_counters(
    session: AsyncSession, session_id: int, *, ok: bool
) -> None:
    obj = await session.get(TestSession, session_id)
    if obj is None:
        return
    obj.done_pairs += 1
    if ok:
        obj.ok_pairs += 1
    else:
        obj.fail_pairs += 1
