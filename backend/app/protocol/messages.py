import struct
from dataclasses import dataclass

from app.protocol.constants import (
    MSG_CONNECT_ACK,
    MSG_CONNECT_RPT,
    TYPE_MA_SE_CNTL,
    TYPE_SE_MA_CNTL,
)

# Wire format is little-endian per BACS_Control.md (Transmit Ordering column).
_HEADER = struct.Struct("<HH")           # type, length
_CTRL_HEADER = struct.Struct("<HBH")     # node_id, msg_type, msg_len


def build_connect_request(node_id: int = 0) -> bytes:
    ctrl = _CTRL_HEADER.pack(node_id, MSG_CONNECT_ACK, 0)
    header = _HEADER.pack(TYPE_SE_MA_CNTL, len(ctrl))
    return header + ctrl


@dataclass(frozen=True)
class ConnectReply:
    source_id: int
    alive: int


def parse_connect_reply(raw: bytes) -> ConnectReply:
    if len(raw) < _HEADER.size + _CTRL_HEADER.size:
        raise ValueError(f"reply too short: {len(raw)} bytes")
    msg_type, _length = _HEADER.unpack_from(raw, 0)
    if msg_type != TYPE_MA_SE_CNTL:
        raise ValueError(f"unexpected type: 0x{msg_type:04x}")
    source_id, ctrl_type, data_len = _CTRL_HEADER.unpack_from(raw, _HEADER.size)
    if ctrl_type != MSG_CONNECT_RPT:
        raise ValueError(f"unexpected msg_type: 0x{ctrl_type:02x}")
    if data_len != 8:
        raise ValueError(f"unexpected data_len: {data_len}")
    body_start = _HEADER.size + _CTRL_HEADER.size
    (alive,) = struct.unpack_from("<Q", raw, body_start)
    return ConnectReply(source_id=source_id, alive=alive)
