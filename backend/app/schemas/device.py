import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

# 전화번호 허용 형식: 숫자와 하이픈만 허용, 예) 800-1200
_PHONE_RE = re.compile(r"^[\d\-]+$")


def _validate_phone(v: str | None) -> str | None:
    if v is not None and v != "" and not _PHONE_RE.match(v):
        raise ValueError("전화번호는 숫자와 하이픈(-)만 허용합니다. 예) 800-1200")
    return v or None


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    ip_address: str
    udp_port: int
    tcp_port: int
    location: str | None
    sido: str | None
    sigungu: str | None
    geo_x: float | None
    geo_y: float | None
    enabled: bool
    # 포트별 전화번호 (0·1=발신TX, 2·3=착신RX)
    port0_phone: str | None
    port1_phone: str | None
    port2_phone: str | None
    port3_phone: str | None


class DeviceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    ip_address: str = Field(min_length=7, max_length=45)
    udp_port: int = Field(default=7788, ge=1, le=65535)
    tcp_port: int = Field(default=7788, ge=1, le=65535)
    location: str | None = Field(default=None, max_length=255)
    sido: str | None = Field(default=None, max_length=32)
    sigungu: str | None = Field(default=None, max_length=64)
    geo_x: float | None = None
    geo_y: float | None = None
    enabled: bool = True
    port0_phone: str | None = Field(default=None, max_length=32)
    port1_phone: str | None = Field(default=None, max_length=32)
    port2_phone: str | None = Field(default=None, max_length=32)
    port3_phone: str | None = Field(default=None, max_length=32)

    @field_validator("port0_phone", "port1_phone", "port2_phone", "port3_phone", mode="before")
    @classmethod
    def validate_phone(cls, v):
        return _validate_phone(v)


class DeviceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    ip_address: str | None = Field(default=None, min_length=7, max_length=45)
    udp_port: int | None = Field(default=None, ge=1, le=65535)
    tcp_port: int | None = Field(default=None, ge=1, le=65535)
    location: str | None = None
    sido: str | None = Field(default=None, max_length=32)
    sigungu: str | None = Field(default=None, max_length=64)
    geo_x: float | None = None
    geo_y: float | None = None
    enabled: bool | None = None
    port0_phone: str | None = Field(default=None, max_length=32)
    port1_phone: str | None = Field(default=None, max_length=32)
    port2_phone: str | None = Field(default=None, max_length=32)
    port3_phone: str | None = Field(default=None, max_length=32)

    @field_validator("port0_phone", "port1_phone", "port2_phone", "port3_phone", mode="before")
    @classmethod
    def validate_phone(cls, v):
        return _validate_phone(v)
