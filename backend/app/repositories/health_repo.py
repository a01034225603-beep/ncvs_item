from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DeviceHealth, HealthStatus


async def upsert(
    session: AsyncSession,
    *,
    bacs_id: int,
    status: HealthStatus,
    checked_at: datetime,
    error: str | None,
) -> None:
    existing = await session.get(DeviceHealth, bacs_id)
    if existing is None:
        # 최초 기록 — ORM 객체 신규 생성
        existing = DeviceHealth(
            bacs_id=bacs_id,
            consecutive_fail=0,
        )
        session.add(existing)

    # 공통 업데이트
    existing.status = status
    existing.last_checked_at = checked_at
    if status == HealthStatus.online:
        existing.last_ok_at = checked_at
        existing.consecutive_fail = 0
        existing.last_error = None
    else:
        existing.consecutive_fail = (existing.consecutive_fail or 0) + 1
        existing.last_error = error
    await session.flush()


async def list_all(session: AsyncSession) -> list[DeviceHealth]:
    result = await session.execute(select(DeviceHealth))
    return list(result.scalars().all())
