from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SessionStatus, TestSession


async def create(
    session: AsyncSession,
    *,
    user_id: int,
    device_ids: list[int],
    total_pairs: int,
    scenario_id: int | None = None,
) -> TestSession:
    obj = TestSession(
        user_id=user_id,
        scenario_id=scenario_id,
        device_ids=device_ids,
        total_pairs=total_pairs,
        status=SessionStatus.queued,
        started_at=datetime.now(timezone.utc),
    )
    session.add(obj)
    await session.flush()
    return obj


async def get(session: AsyncSession, session_id: int) -> TestSession | None:
    return await session.get(TestSession, session_id)


async def list_all(session: AsyncSession) -> list[TestSession]:
    """전체 세션 목록 (최신순)"""
    result = await session.execute(
        select(TestSession).order_by(TestSession.id.desc())
    )
    return list(result.scalars().all())


async def list_by_scenario(session: AsyncSession, scenario_id: int) -> list[TestSession]:
    """시나리오 ID 기준 세션 목록 (최신순)"""
    result = await session.execute(
        select(TestSession)
        .where(TestSession.scenario_id == scenario_id)
        .order_by(TestSession.id.desc())
    )
    return list(result.scalars().all())


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
        obj.finished_at = datetime.now(timezone.utc)


async def increment_counters(
    session: AsyncSession, session_id: int, *, ok: bool
) -> None:
    """done_pairs / ok_pairs / fail_pairs 를 원자적 SQL 증분으로 갱신한다.

    ORM read-modify-write 대신 UPDATE col = col + 1 방식을 사용하므로
    다수 페어가 동시에 완료되더라도 데드락 없이 안전하게 처리된다.
    """
    stmt = (
        update(TestSession)
        .where(TestSession.id == session_id)
        .values(
            done_pairs=TestSession.done_pairs + 1,
            ok_pairs=TestSession.ok_pairs + (1 if ok else 0),
            fail_pairs=TestSession.fail_pairs + (0 if ok else 1),
        )
        # ORM autoflush 를 우회하여 불필요한 flush 충돌 방지
        .execution_options(synchronize_session=False)
    )
    await session.execute(stmt)
