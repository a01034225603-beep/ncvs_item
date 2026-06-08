"""
BACS 장비 CRUD API 라우터 — /devices

엔드포인트:
  GET    /devices          — 등록된 장비 전체 목록 조회
  POST   /devices          — 새 장비 등록
  PUT    /devices/{id}     — 장비 정보 수정
  DELETE /devices/{id}     — 장비 삭제
  GET    /devices/health   — 전체 장비의 UDP 헬스체크 최신 상태 조회
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.models import User
from app.repositories import device_repo, health_repo
from app.schemas.device import DeviceCreate, DeviceOut, DeviceUpdate
from app.schemas.health import HealthOut

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("", response_model=list[DeviceOut])
async def list_devices(
    _: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
):
    return await device_repo.list_all(session)


@router.get("/health", response_model=list[HealthOut])
async def list_health(
    _: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
):
    return await health_repo.list_all(session)


@router.post("", response_model=DeviceOut, status_code=status.HTTP_201_CREATED)
async def create_device(
    body: DeviceCreate,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """장비 등록"""
    return await device_repo.create(session, body)


@router.put("/{device_id}", response_model=DeviceOut)
async def update_device(
    device_id: int,
    body: DeviceUpdate,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """장비 수정"""
    device = await device_repo.update(session, device_id, body)
    if device is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "device not found")
    return device


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    device_id: int,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """장비 삭제"""
    deleted = await device_repo.delete(session, device_id)
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "device not found")
