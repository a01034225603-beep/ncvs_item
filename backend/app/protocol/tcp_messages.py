"""
BACS TCP 제어 패킷 빌드·파싱 모듈
출처: docs/BACS_Control.md §1.3

메시지 구조 (공통):
  Header  : Type(2, LE) + DataLength(2, LE)
  Control : NodeID(2, LE) + MsgType(1) + MsgDataLen(2, LE) + MsgData(n)
"""
from __future__ import annotations

import struct
from enum import Enum


# ─── 결과 코드 Enum ────────────────────────────────────────────────────────

class CallResult(str, Enum):
    OK   = "OK"    # 0x0011 — 호출 성공
    NK   = "NK"    # 0x0013 또는 0x0016 — DTMF 일부 소실
    BUSY = "BUSY"  # 0x0015 — 중복 요청
    FAIL = "FAIL"  # 0x0023 또는 알 수 없는 코드 — DTMF 완전 소실


# ─── 상수 ─────────────────────────────────────────────────────────────────

_TYPE_SE_MA  = 0x1001   # Server → BACS
_TYPE_MA_SE_MASTER = 0x0101   # BACS(Master) → Server
_TYPE_MA_SE_SLAVE  = 0x0201   # BACS(Slave) → Server

_MSG_CONNECT_LEVEL = 0x66   # SE_MA_Connect_Level_REQ
_MSG_STARTUP_RPT   = 0x90   # MA_SE_Start_Up_RPT
_MSG_ERROR_RPT     = 0x91   # MA_SE_Error_RPT
_MSG_CALL_REQ      = 0x50   # SE_MA_CALL_REQ
_MSG_CALL_RPT      = 0xD0   # MA_SE_CALL_RPT

_CONNECT_LEVEL_DATA_LEN = 9    # Header Data Length (NodeID+Type+MsgLen+MsgData)
_CALL_REQ_DATA_LEN      = 23   # 0x17

# CALL_RPT 결과코드 매핑
# MsgData 구조: Port(1) + ResultCode(1) — 결과코드는 하위 1바이트
_CALL_RESULT_MAP: dict[int, CallResult] = {
    0x11: CallResult.OK,
    0x13: CallResult.NK,
    0x16: CallResult.NK,
    0x15: CallResult.BUSY,
    0x23: CallResult.FAIL,
}


# ─── 패킷 빌드 ────────────────────────────────────────────────────────────

def build_connect_level_req() -> bytes:
    """
    SE_MA_Connect_Level_REQ 패킷 빌드 (13바이트 고정).

    01 10 | 09 00 | 00 00 | 66 | 04 00 | e7 e7 00 00
    """
    node_id = 0
    level = 0x0000E7E7
    # Control 영역: NodeID(2) + MsgType(1) + MsgDataLen(2) + Level(4) = 9바이트
    control = struct.pack("<HBH", node_id, _MSG_CONNECT_LEVEL, 4) + struct.pack("<I", level)
    # Header: Type(2) + DataLength(2)
    header = struct.pack("<HH", _TYPE_SE_MA, len(control))
    return header + control


# BACS 명세: CALL_REQ의 Node ID는 항상 1 고정 (모든 장비 공통)
_CALL_NODE_ID: int = 1


def build_call_req(*, port: int, phone: str | None) -> bytes:
    """
    SE_MA_CALL_REQ 패킷 빌드 (27바이트 고정).

    Node ID는 항상 1로 고정 (_CALL_NODE_ID).

    Args:
        port:  발신 포트 번호 (0 또는 1).
        phone: dst 착신 포트의 전화번호 (None이면 전부 0x00).
    """
    # 전화번호 → 최대 16바이트 ASCII, 나머지 0 패딩
    if phone:
        phone_bytes = phone.encode("ascii", errors="replace")[:16]
        phone_len = len(phone_bytes)
    else:
        phone_bytes = b""
        phone_len = 0
    phone_padded = phone_bytes.ljust(16, b"\x00")

    # MsgData: Port(1) + PhoneLen(1) + PhoneNum(16) = 18바이트
    msg_data = struct.pack("BB", port, phone_len) + phone_padded
    # Control 영역: NodeID(2) + MsgType(1) + MsgDataLen(2) + MsgData(18) = 23바이트
    control = struct.pack("<HBH", _CALL_NODE_ID, _MSG_CALL_REQ, 18) + msg_data
    header = struct.pack("<HH", _TYPE_SE_MA, len(control))
    return header + control


# ─── 패킷 파싱 ────────────────────────────────────────────────────────────

def is_error_rpt(data: bytes) -> bool:
    """수신된 프레임이 ERROR_RPT(0x91)인지 여부를 반환한다."""
    return len(data) >= 7 and data[6] == _MSG_ERROR_RPT


def parse_error_rpt(data: bytes) -> tuple[int, str]:
    """
    MA_SE_Error_RPT 패킷에서 (err_code, err_text) 를 추출한다.

    Returns:
        (err_code, err_text) — 파싱 실패 시 (0, "")
    """
    try:
        err_code = struct.unpack_from("<H", data, 9)[0] if len(data) >= 11 else 0
        err_text = data[11:].rstrip(b"\x00").decode("ascii", errors="replace") if len(data) > 11 else ""
        return err_code, err_text
    except Exception:  # noqa: BLE001
        return 0, ""


def parse_startup_response(data: bytes) -> tuple[bool, int | None]:
    """
    TCP 접속 후 BACS에서 오는 첫 응답을 파싱한다.

    Returns:
        (True, None)       — MA_SE_Start_Up_RPT (0x90) 수신 → 제어권 획득
        (False, err_code)  — MA_SE_Error_RPT (0x91) 수신 → 거부, err_code는 300~302
        (False, None)      — 파싱 불가
    """
    # 최소 길이: Header(4) + NodeID(2) + MsgType(1) = 7바이트
    if len(data) < 7:
        return False, None
    try:
        # Header
        _type, data_len = struct.unpack_from("<HH", data, 0)
        # Control Header
        node_id, msg_type, msg_data_len = struct.unpack_from("<HBH", data, 4)
        if msg_type == _MSG_STARTUP_RPT:
            return True, None
        if msg_type == _MSG_ERROR_RPT:
            # Error code: 첫 2바이트 (MsgData 시작)
            if len(data) >= 9 + 2:
                err_code = struct.unpack_from("<H", data, 9)[0]
            else:
                err_code = 0
            return False, err_code
    except struct.error:
        pass
    return False, None


def parse_packet_for_display(data: bytes) -> dict:
    """
    임의의 BACS TCP 패킷을 BACS_Control.md §1.3 기준으로 파싱하여
    UI 표시용 딕셔너리를 반환한다.

    출력 필드 (공통):
        pkt_type  : Header Type (예: "0x1001")
        data_len  : Header DataLength
        node_id   : Control NodeID
        msg_type  : 메시지 타입 hex + 설명 (예: "0x66 CONNECT_LEVEL")
        msg_data_len: MsgDataLength

    패킷별 추가 필드:
        CONNECT_LEVEL: level
        STARTUP_RPT : (없음)
        ERROR_RPT   : err_code, err_code_desc
        CALL_REQ    : port, phone_len, phone
        CALL_RPT    : port, result_code, result_desc
    """
    if len(data) < 7:
        return {"raw_len": len(data), "parse_error": "too short"}

    try:
        pkt_type = struct.unpack_from("<H", data, 0)[0]
        data_len = struct.unpack_from("<H", data, 2)[0]
        node_id  = struct.unpack_from("<H", data, 4)[0]
        msg_type = data[6]
        msg_data_len = struct.unpack_from("<H", data, 7)[0] if len(data) >= 9 else 0

        # MSG_TYPE 설명 매핑
        _MSG_DESC = {
            0x66: "CONNECT_LEVEL",
            0x90: "STARTUP_RPT",
            0x91: "ERROR_RPT",
            0x50: "CALL_REQ",
            0xD0: "CALL_RPT",
        }

        result: dict = {
            "pkt_type":     f"0x{pkt_type:04X}",
            "data_len":     data_len,
            "node_id":      node_id,
            "msg_type":     f"0x{msg_type:02X} {_MSG_DESC.get(msg_type, '?')}",
            "msg_data_len": msg_data_len,
        }

        if msg_type == _MSG_CONNECT_LEVEL and len(data) >= 13:
            level = struct.unpack_from("<I", data, 9)[0]
            result["level"] = f"0x{level:08X}"

        elif msg_type == _MSG_ERROR_RPT and len(data) >= 11:
            err_code = struct.unpack_from("<H", data, 9)[0]
            _ERR_DESC = {300: "제어권 빼앗김", 301: "제어권 획득", 302: "연결 거부"}
            result["err_code"]      = err_code
            result["err_code_desc"] = _ERR_DESC.get(err_code, f"unknown({err_code})")

        elif msg_type == _MSG_CALL_REQ and len(data) >= 12:
            port      = data[9]
            phone_len = data[10]
            phone_raw = data[11:11 + phone_len]
            result["port"]      = port
            result["phone_len"] = phone_len
            result["phone"]     = phone_raw.decode("ascii", errors="replace") if phone_len else ""

        elif msg_type == _MSG_CALL_RPT and len(data) >= 11:
            port        = data[9]
            result_code = data[10]
            _RESULT_DESC = {
                0x11: "OK (호출성공)",
                0x13: "NK (DTMF일부소실)",
                0x16: "NK (DTMF일부소실)",
                0x15: "BUSY (중복요청)",
                0x23: "FAIL (DTMF완전소실)",
            }
            result["port"]        = port
            result["result_code"] = f"0x{result_code:02X}"
            result["result_desc"] = _RESULT_DESC.get(result_code, f"FAIL (unknown 0x{result_code:02X})")

        return result

    except Exception as exc:  # noqa: BLE001
        return {"parse_error": str(exc)}


def parse_call_rpt(data: bytes) -> CallResult:
    """
    MA_SE_CALL_RPT 패킷을 파싱하여 CallResult를 반환한다.

    패킷 구조 (11바이트):
      01 02 | 07 00 | NodeID(2) | d0 | 02 00 | Port(1) + Result(1)

    ⚠️ 실장비 확인 결과: MsgData = Port(1바이트) + ResultCode(1바이트)
       예) Port 0: 00 11 → result=0x11=OK
           Port 1: 01 11 → result=0x11=OK
    """
    # 최소 길이: Header(4) + NodeID(2) + MsgType(1) + MsgDataLen(2) + Port(1) + Result(1) = 11
    if len(data) < 11:
        return CallResult.FAIL
    try:
        result_code = data[10]  # 하위 1바이트가 결과코드
    except IndexError:
        return CallResult.FAIL
    return _CALL_RESULT_MAP.get(result_code, CallResult.FAIL)
