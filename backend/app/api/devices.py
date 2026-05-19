from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.models import User
from app.repositories import device_repo, health_repo
from app.schemas.device import DeviceOut
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
