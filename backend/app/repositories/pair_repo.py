from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    PairLatestResult,
    PairLatestStatus,
    PairStatus,
    TestSessionPair,
)


async def bulk_insert_pending(
    session: AsyncSession,
    session_id: int,
    ordered_pairs: list[tuple[int, int]],
    *,
    round_numbers: list[int] | None = None,
) -> None:
    """페어 목록을 pending 상태로 일괄 삽입한다.

    round_numbers 를 전달하면 각 페어에 라운드 번호를 부여한다.
    전달하지 않으면 전부 round_number=1 로 저장된다.
    """
    if round_numbers is None:
        round_numbers = [1] * len(ordered_pairs)
    session.add_all(
        TestSessionPair(
            session_id=session_id,
            src_bacs_id=src,
            dst_bacs_id=dst,
            round_number=rn,
            status=PairStatus.pending,
        )
        for (src, dst), rn in zip(ordered_pairs, round_numbers)
    )
    await session.flush()


async def list_pending_for_session(
    session: AsyncSession, session_id: int
) -> list[TestSessionPair]:
    result = await session.execute(
        select(TestSessionPair)
        .where(
            TestSessionPair.session_id == session_id,
            TestSessionPair.status == PairStatus.pending,
        )
        # 라운드 오름차순 → id 오름차순 고정 — 비결정적 반환 방지
        .order_by(TestSessionPair.round_number, TestSessionPair.id)
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


async def mark_pending_as_skipped(session: AsyncSession, session_id: int) -> None:
    """세션의 남은 pending 페어를 모두 skipped 로 일괄 처리한다.

    호출 중단 시 아직 실행되지 않은 페어를 skipped 상태로 변경한다.
    원자적 UPDATE 를 사용하므로 대기 중인 다른 쿼리와 충돌하지 않는다.
    """
    stmt = (
        update(TestSessionPair)
        .where(
            TestSessionPair.session_id == session_id,
            TestSessionPair.status == PairStatus.pending,
        )
        .values(status=PairStatus.skipped)
        .execution_options(synchronize_session=False)
    )
    await session.execute(stmt)


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
