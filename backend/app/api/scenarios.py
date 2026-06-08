"""
호출시험 시나리오 CRUD API 라우터 — /scenarios

엔드포인트:
  GET    /scenarios       — 시나리오 전체 목록
  GET    /scenarios/{id}  — 특정 시나리오 조회
  POST   /scenarios       — 새 시나리오 등록 (발신/착신 장비 ID 조합 저장)
  PATCH  /scenarios/{id}  — 시나리오 수정
  DELETE /scenarios/{id}  — 시나리오 삭제

시나리오 = 호출시험에서 사용할 '(sender 장비 목록) × (receiver 장비 목록)' 조합.
시나리오 실행 요청 시 session_service 가 페어를 생성하고 스케줄러에 등록한다.
"""
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
