from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BacsDevice


async def list_enabled(session: AsyncSession) -> list[BacsDevice]:
    result = await session.execute(select(BacsDevice).where(BacsDevice.enabled.is_(True)))
    return list(result.scalars().all())


async def list_all(session: AsyncSession) -> list[BacsDevice]:
    result = await session.execute(select(BacsDevice))
    return list(result.scalars().all())


async def get_by_ids(session: AsyncSession, ids: list[int]) -> list[BacsDevice]:
    if not ids:
        return []
    result = await session.execute(select(BacsDevice).where(BacsDevice.id.in_(ids)))
    return list(result.scalars().all())
