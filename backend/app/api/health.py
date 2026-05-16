from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.models import User

router = APIRouter(prefix="/health", tags=["health"])


@router.post("/refresh", status_code=202)
async def refresh(
    request: Request,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await request.app.state.health_svc.run_once(session)
    return {"status": "refreshed"}
