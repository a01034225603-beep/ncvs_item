from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scenario import Scenario
from app.schemas.scenario import ScenarioCreate, ScenarioUpdate


async def list_all(db: AsyncSession) -> list[Scenario]:
    """시나리오 전체 목록 (최신순)."""
    result = await db.execute(select(Scenario).order_by(Scenario.id.desc()))
    return list(result.scalars().all())


async def get(db: AsyncSession, scenario_id: int) -> Scenario | None:
    result = await db.execute(select(Scenario).where(Scenario.id == scenario_id))
    return result.scalar_one_or_none()


async def create(db: AsyncSession, data: ScenarioCreate) -> Scenario:
    """새 시나리오 저장."""
    scenario = Scenario(
        name=data.name,
        sender_device_ids=data.sender_device_ids,
        receiver_device_ids=data.receiver_device_ids,
    )
    db.add(scenario)
    await db.commit()
    await db.refresh(scenario)
    return scenario


async def update(db: AsyncSession, scenario_id: int, data: ScenarioUpdate) -> Scenario | None:
    scenario = await get(db, scenario_id)
    if not scenario:
        return None
    if data.name is not None:
        scenario.name = data.name
    if data.sender_device_ids is not None:
        scenario.sender_device_ids = data.sender_device_ids
    if data.receiver_device_ids is not None:
        scenario.receiver_device_ids = data.receiver_device_ids
    scenario.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(scenario)
    return scenario


async def delete(db: AsyncSession, scenario_id: int) -> bool:
    scenario = await get(db, scenario_id)
    if not scenario:
        return False
    await db.delete(scenario)
    await db.commit()
    return True
