from pydantic import BaseModel, Field


class ScenarioCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    sender_device_ids: list[int] = Field(default_factory=list)
    receiver_device_ids: list[int] = Field(default_factory=list)


class ScenarioUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    sender_device_ids: list[int] | None = None
    receiver_device_ids: list[int] | None = None


class ScenarioOut(BaseModel):
    id: int
    name: str
    sender_device_ids: list[int]
    receiver_device_ids: list[int]
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_obj(cls, obj) -> "ScenarioOut":  # type: ignore[override]
        return cls(
            id=obj.id,
            name=obj.name,
            sender_device_ids=obj.sender_device_ids or [],
            receiver_device_ids=obj.receiver_device_ids or [],
            created_at=obj.created_at.isoformat() if obj.created_at else "",
            updated_at=obj.updated_at.isoformat() if obj.updated_at else "",
        )
