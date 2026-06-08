"""
호출시험 세션 생성 서비스.

역할:
  create_session_from_scenario():
    시나리오의 sender x receiver 장비 조합으로 페어를 생성하고
    DB에 TestSession + TestSessionPair 행을 삽입한 후 반환한다.
    실행은 CrossTestScheduler 에 위임하며 이 함수는 생성만 담당한다.

  cancel_session():
    세션 상태를 cancelled 로 변경한다.
    실제 실행 중단은 scheduler 루프가 다음 순회 시 감지하여 처리한다.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SessionStatus, TestSession
from app.repositories import pair_repo, session_repo


async def create_session_from_scenario(
    session: AsyncSession,
    *,
    user_id: int,
    scenario_id: int,
    sender_device_ids: list[int],
    receiver_device_ids: list[int],
) -> TestSession:
    """
    시나리오 기준으로 호출시험 세션을 생성한다.

    발신(sender) 장비 각각이 착신(receiver) 장비 각각에 대해 단방향 페어를 구성한다.
    예) sender=[A,B], receiver=[C,D] → (A→C), (A→D), (B→C), (B→D) 4쌍
    """
    if not sender_device_ids or not receiver_device_ids:
        raise ValueError("sender and receiver device lists must not be empty")

    # sender × receiver 단방향 페어 (순서 있는 곱)
    ordered_pairs = [
        (src_id, dst_id)
        for src_id in sender_device_ids
        for dst_id in receiver_device_ids
        if src_id != dst_id  # 자기 자신과의 페어 제외
    ]
    if not ordered_pairs:
        raise ValueError("no valid pairs: sender and receiver must differ")

    all_device_ids = list(dict.fromkeys(sender_device_ids + receiver_device_ids))
    test_session = await session_repo.create(
        session,
        user_id=user_id,
        scenario_id=scenario_id,
        device_ids=all_device_ids,
        total_pairs=len(ordered_pairs),
    )
    await pair_repo.bulk_insert_pending(session, test_session.id, ordered_pairs)
    await session.commit()
    return test_session


async def cancel_session(session: AsyncSession, session_id: int) -> None:
    await session_repo.mark_finished(session, session_id, SessionStatus.cancelled)
    await session.commit()
