from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.models import User
from app.repositories import pair_repo, session_repo
from app.schemas.pair import PairOut
from app.schemas.session import CreateSessionRequest, SessionOut
from app.services.session_service import cancel_session, create_session

router = APIRouter(prefix="/tests", tags=["tests"])


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def create(
    body: CreateSessionRequest,
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    ts = await create_session(session, user_id=user.id, device_ids=body.device_ids)
    request.app.state.crosstest.submit(ts.id)
    return ts


@router.get("/{session_id}", response_model=SessionOut)
async def get_one(
    session_id: int,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    ts = await session_repo.get(session, session_id)
    if ts is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "session not found")
    return ts


@router.get("/{session_id}/pairs", response_model=list[PairOut])
async def list_pairs(
    session_id: int,
    status_filter: str | None = None,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if status_filter == "running":
        return await pair_repo.list_running(session, session_id)
    if status_filter == "pending":
        return await pair_repo.list_pending_for_session(session, session_id)
    raise HTTPException(status.HTTP_400_BAD_REQUEST, "use status_filter=running|pending")


@router.post("/{session_id}/cancel", status_code=status.HTTP_202_ACCEPTED)
async def cancel(
    session_id: int,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await cancel_session(session, session_id)
    return {"status": "cancelled"}
