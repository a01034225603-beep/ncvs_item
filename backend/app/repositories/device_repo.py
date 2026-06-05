from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BacsDevice
from app.schemas.device import DeviceCreate, DeviceUpdate


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


async def get(session: AsyncSession, device_id: int) -> BacsDevice | None:
    return await session.get(BacsDevice, device_id)


async def create(session: AsyncSession, data: DeviceCreate) -> BacsDevice:
    """새 장비 생성"""
    device = BacsDevice(**data.model_dump())
    session.add(device)
    await session.commit()
    await session.refresh(device)
    return device


async def update(session: AsyncSession, device_id: int, data: DeviceUpdate) -> BacsDevice | None:
    """장비 부분 수정 (None 필드 제외)"""
    device = await session.get(BacsDevice, device_id)
    if device is None:
        return None
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(device, field, value)
    await session.commit()
    await session.refresh(device)
    return device


async def delete(session: AsyncSession, device_id: int) -> bool:
    """장비 삭제. 존재하지 않으면 False"""
    device = await session.get(BacsDevice, device_id)
    if device is None:
        return False
    await session.delete(device)
    await session.commit()
    return True
