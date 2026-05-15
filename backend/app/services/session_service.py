from itertools import permutations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SessionStatus, TestSession
from app.repositories import pair_repo, session_repo


async def create_session(
    session: AsyncSession, *, user_id: int, device_ids: list[int]
) -> TestSession:
    if len(device_ids) < 2:
        raise ValueError("at least 2 devices required")
    ordered_pairs = list(permutations(device_ids, 2))  # (src, dst) directed pairs
    test_session = await session_repo.create(
        session,
        user_id=user_id,
        device_ids=device_ids,
        total_pairs=len(ordered_pairs),
    )
    await pair_repo.bulk_insert_pending(session, test_session.id, ordered_pairs)
    await session.commit()
    return test_session


async def cancel_session(session: AsyncSession, session_id: int) -> None:
    await session_repo.mark_finished(session, session_id, SessionStatus.cancelled)
    await session.commit()
