from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert as mysql_insert
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
    stmt = mysql_insert(DeviceHealth).values(
        bacs_id=bacs_id,
        status=status,
        last_checked_at=checked_at,
        last_ok_at=checked_at if status == HealthStatus.ok else None,
        last_error=error,
        consecutive_fail=0 if status == HealthStatus.ok else 1,
    )
    existing = await session.get(DeviceHealth, bacs_id)
    if existing is None:
        await session.execute(stmt)
    else:
        existing.status = status
        existing.last_checked_at = checked_at
        if status == HealthStatus.ok:
            existing.last_ok_at = checked_at
            existing.consecutive_fail = 0
            existing.last_error = None
        else:
            existing.consecutive_fail += 1
            existing.last_error = error
    await session.flush()


async def list_all(session: AsyncSession) -> list[DeviceHealth]:
    result = await session.execute(select(DeviceHealth))
    return list(result.scalars().all())
