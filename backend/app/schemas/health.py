"""
UDP 헬스체크 상태 응답 스키마.

HealthOut: GET /devices/health 응답 (bacs_id, status, checked_at 포함)
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import HealthStatus


class HealthOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    bacs_id: int
    status: HealthStatus
    last_checked_at: datetime | None
    last_ok_at: datetime | None
    last_error: str | None
