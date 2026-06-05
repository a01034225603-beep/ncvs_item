from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.repositories import scenario_repo
from app.schemas.scenario import ScenarioCreate, ScenarioOut, ScenarioUpdate

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.get("", response_model=list[ScenarioOut])
async def list_scenarios(db: AsyncSession = Depends(get_session)):
    rows = await scenario_repo.list_all(db)
    return [ScenarioOut.from_orm_obj(r) for r in rows]


@router.get("/{scenario_id}", response_model=ScenarioOut)
async def get_scenario(scenario_id: int, db: AsyncSession = Depends(get_session)):
    row = await scenario_repo.get(db, scenario_id)
    if not row:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return ScenarioOut.from_orm_obj(row)


@router.post("", response_model=ScenarioOut, status_code=status.HTTP_201_CREATED)
async def create_scenario(body: ScenarioCreate, db: AsyncSession = Depends(get_session)):
    row = await scenario_repo.create(db, body)
    return ScenarioOut.from_orm_obj(row)


@router.put("/{scenario_id}", response_model=ScenarioOut)
async def update_scenario(
    scenario_id: int, body: ScenarioUpdate, db: AsyncSession = Depends(get_session)
):
    row = await scenario_repo.update(db, scenario_id, body)
    if not row:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return ScenarioOut.from_orm_obj(row)


@router.delete("/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scenario(scenario_id: int, db: AsyncSession = Depends(get_session)):
    ok = await scenario_repo.delete(db, scenario_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Scenario not found")
