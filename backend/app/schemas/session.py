from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import PairStatus, SessionStatus


class PairStateItem(BaseModel):
    """SSE 진행 현황용 — 페어 한 개의 현재 상태."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    src_bacs_id: int
    dst_bacs_id: int
    status: PairStatus
    error_message: str | None


class CreateSessionRequest(BaseModel):
    device_ids: list[int] = Field(min_length=2)


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    scenario_id: int | None = None   # 시나리오 기반 세션이면 해당 ID
    status: SessionStatus
    device_ids: list[int]
    total_pairs: int
    done_pairs: int
    ok_pairs: int
    fail_pairs: int
    started_at: datetime | None
    finished_at: datetime | None


class SessionWithPairsOut(SessionOut):
    """stream SSE 용 — SessionOut + 전체 페어 상태 목록."""
    pairs: list[PairStateItem]
