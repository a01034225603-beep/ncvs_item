from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import PairLatestStatus, PairStatus


class PairOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    src_bacs_id: int
    dst_bacs_id: int
    status: PairStatus
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None


class MatrixCell(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    src_bacs_id: int
    dst_bacs_id: int
    status: PairLatestStatus
    tested_at: datetime
    error_message: str | None
