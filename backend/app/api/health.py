"""
UDP 헬스체크 수동 갱신 API 라우터 — /health

엔드포인트:
  POST /health/refresh — 전체 장비에 대해 UDP 헬스체크를 즉시 실행한다.
                        (헬스체크는 평소 60초 주기로 자동 실행되지만,
                         수동으로 즉시 갱신할 때 사용한다.)
"""
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
