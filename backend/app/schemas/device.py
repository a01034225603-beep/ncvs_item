from pydantic import BaseModel, ConfigDict


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    node_id: int
    ip_address: str
    udp_port: int
    tcp_port: int
    location: str | None
    enabled: bool
