from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    PairLatestResult,
    PairLatestStatus,
    PairStatus,
    TestSessionPair,
)


async def bulk_insert_pending(
    session: AsyncSession, session_id: int, ordered_pairs: list[tuple[int, int]]
) -> None:
    session.add_all(
        TestSessionPair(
            session_id=session_id, src_bacs_id=src, dst_bacs_id=dst, status=PairStatus.pending
        )
        for src, dst in ordered_pairs
    )
    await session.flush()


async def list_pending_for_session(
    session: AsyncSession, session_id: int
) -> list[TestSessionPair]:
    result = await session.execute(
        select(TestSessionPair).where(
            TestSessionPair.session_id == session_id,
            TestSessionPair.status == PairStatus.pending,
        )
    )
    return list(result.scalars().all())


async def list_running(session: AsyncSession, session_id: int) -> list[TestSessionPair]:
    result = await session.execute(
        select(TestSessionPair).where(
            TestSessionPair.session_id == session_id,
            TestSessionPair.status == PairStatus.running,
        )
    )
    return list(result.scalars().all())


async def list_all_for_session(
    session: AsyncSession, session_id: int
) -> list[TestSessionPair]:
    """세션의 전체 페어 목록을 상태 무관하게 반환한다 (SSE 진행 현황 조회용)."""
    result = await session.execute(
        select(TestSessionPair).where(
            TestSessionPair.session_id == session_id,
        )
    )
    return list(result.scalars().all())


async def mark_running(session: AsyncSession, pair_id: int) -> None:
    obj = await session.get(TestSessionPair, pair_id)
    if obj is not None:
        obj.status = PairStatus.running
        obj.started_at = datetime.now(timezone.utc)


async def mark_result(
    session: AsyncSession, pair_id: int, *, ok: bool, error: str | None
) -> None:
    obj = await session.get(TestSessionPair, pair_id)
    if obj is None:
        return
    obj.status = PairStatus.ok if ok else PairStatus.fail
    obj.finished_at = datetime.now(timezone.utc)
    obj.error_message = error


async def upsert_latest(
    session: AsyncSession,
    *,
    src_bacs_id: int,
    dst_bacs_id: int,
    ok: bool,
    error: str | None,
    session_id: int,
) -> None:
    existing = await session.get(PairLatestResult, (src_bacs_id, dst_bacs_id))
    status = PairLatestStatus.ok if ok else PairLatestStatus.fail
    now = datetime.now(timezone.utc)
    if existing is None:
        session.add(
            PairLatestResult(
                src_bacs_id=src_bacs_id,
                dst_bacs_id=dst_bacs_id,
                status=status,
                tested_at=now,
                session_id=session_id,
                error_message=error,
            )
        )
    else:
        existing.status = status
        existing.tested_at = now
        existing.session_id = session_id
        existing.error_message = error
    await session.flush()
