from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.models import PairLatestResult, User
from app.schemas.pair import MatrixCell

router = APIRouter(prefix="/pair-matrix", tags=["matrix"])


@router.get("", response_model=list[MatrixCell])
async def get_matrix(
    device_ids: list[int] = Query(...),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(PairLatestResult).where(
            PairLatestResult.src_bacs_id.in_(device_ids),
            PairLatestResult.dst_bacs_id.in_(device_ids),
        )
    )
    return list(result.scalars().all())
