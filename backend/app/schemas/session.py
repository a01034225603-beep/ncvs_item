from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import SessionStatus


class CreateSessionRequest(BaseModel):
    device_ids: list[int] = Field(min_length=2)


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: SessionStatus
    device_ids: list[int]
    total_pairs: int
    done_pairs: int
    ok_pairs: int
    fail_pairs: int
    started_at: datetime | None
    finished_at: datetime | None
