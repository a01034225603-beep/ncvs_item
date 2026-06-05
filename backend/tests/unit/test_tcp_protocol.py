"""
TCP 호출시험 프로토콜 패킷 빌드·파싱 단위 테스트
TDD: 이 파일은 구현 전에 먼저 작성됨 — 처음 실행 시 ImportError/실패가 정상

패킷 명세 출처: docs/BACS_Control.md §1.3
"""
import pytest

from app.protocol.tcp_messages import (
    build_connect_level_req,
    build_call_req,
    parse_startup_response,
    parse_call_rpt,
    CallResult,
)


# ─── SE_MA_Connect_Level_REQ (13바이트) ─────────────────────────────────────

class TestBuildConnectLevelReq:
    def test_길이_13바이트(self):
        pkt = build_connect_level_req()
        assert len(pkt) == 13

    def test_헤더_타입_0x1001(self):
        # Little-endian: 01 10
        pkt = build_connect_level_req()
        assert pkt[0:2] == b"\x01\x10"

    def test_데이터_길이_9(self):
        # Length 필드 = 9 (Little-endian: 09 00)
        pkt = build_connect_level_req()
        assert pkt[2:4] == b"\x09\x00"

    def test_노드ID_0(self):
        pkt = build_connect_level_req()
        assert pkt[4:6] == b"\x00\x00"

    def test_메시지타입_0x66(self):
        pkt = build_connect_level_req()
        assert pkt[6] == 0x66

    def test_메시지길이_4(self):
        # Message Length = 4 (Little-endian: 04 00)
        pkt = build_connect_level_req()
        assert pkt[7:9] == b"\x04\x00"

    def test_레벨값_0xe7e7(self):
        # Level = 0x0000e7e7 (Little-endian: e7 e7 00 00)
        pkt = build_connect_level_req()
        assert pkt[9:13] == b"\xe7\xe7\x00\x00"


# ─── MA_SE_Start_Up_RPT / MA_SE_Error_RPT 파싱 ──────────────────────────────

class TestParseStartupResponse:
    def test_startup_rpt_성공(self):
        # MA_SE_Start_Up_RPT: 01 01 05 00 00 00 90 00 00
        pkt = bytes([0x01, 0x01, 0x05, 0x00, 0x00, 0x00, 0x90, 0x00, 0x00])
        ok, err_code = parse_startup_response(pkt)
        assert ok is True
        assert err_code is None

    def test_error_rpt_302_접속거부(self):
        # MA_SE_Error_RPT: err_code=302(0x012E) Little-endian → 2E 01
        # Header: 01 01 | length | 00 00 | 91 | msg_len | 2E 01 | (no msg string)
        err_code_bytes = b"\x2e\x01"  # 302 LE
        msg_len = 2
        data_len = 5 + msg_len  # NodeID(2)+Type(1)+MsgLen(2)+Data
        pkt = (
            b"\x01\x01"
            + (data_len).to_bytes(2, "little")
            + b"\x00\x00"   # Node ID
            + b"\x91"        # ERROR_RPT
            + msg_len.to_bytes(2, "little")
            + err_code_bytes
        )
        ok, err_code = parse_startup_response(pkt)
        assert ok is False
        assert err_code == 302

    def test_error_rpt_300_제어권_빼앗김(self):
        err_code_bytes = b"\x2c\x01"  # 300 LE
        msg_len = 2
        data_len = 5 + msg_len
        pkt = (
            b"\x01\x01"
            + (data_len).to_bytes(2, "little")
            + b"\x00\x00"
            + b"\x91"
            + msg_len.to_bytes(2, "little")
            + err_code_bytes
        )
        ok, err_code = parse_startup_response(pkt)
        assert ok is False
        assert err_code == 300

    def test_알_수_없는_패킷(self):
        # 길이 부족 등 — ok=False, err_code=None
        ok, err_code = parse_startup_response(b"\xff\xff")
        assert ok is False
        assert err_code is None


# ─── SE_MA_CALL_REQ (27바이트) ───────────────────────────────────────────────

class TestBuildCallReq:
    def test_길이_27바이트(self):
        pkt = build_call_req(port=0, phone="800-1200")
        assert len(pkt) == 27

    def test_헤더_타입_0x1001(self):
        pkt = build_call_req(port=0, phone="800-1200")
        assert pkt[0:2] == b"\x01\x10"

    def test_데이터_길이_23(self):
        # Length = 23 (0x17): NodeID(2)+Type(1)+MsgLen(2)+Data(18) = 23
        pkt = build_call_req(port=0, phone="800-1200")
        assert pkt[2:4] == b"\x17\x00"

    def test_메시지타입_0x50(self):
        pkt = build_call_req(port=0, phone="800-1200")
        assert pkt[6] == 0x50

    def test_메시지_데이터_길이_18(self):
        pkt = build_call_req(port=0, phone="800-1200")
        assert pkt[7:9] == b"\x12\x00"

    def test_포트값_삽입(self):
        pkt0 = build_call_req(port=0, phone="800-1200")
        pkt1 = build_call_req(port=1, phone="800-1200")
        assert pkt0[9] == 0
        assert pkt1[9] == 1

    def test_전화번호_길이_필드(self):
        # "800-1200" = 8자 (하이픈 포함)
        pkt = build_call_req(port=0, phone="800-1200")
        assert pkt[10] == 8

    def test_전화번호_16바이트_패딩(self):
        # "800-1200" → 8바이트 ASCII + 8바이트 0x00 패딩
        pkt = build_call_req(port=0, phone="800-1200")
        phone_bytes = pkt[11:27]
        assert phone_bytes[:8] == b"800-1200"
        assert phone_bytes[8:] == b"\x00" * 8

    def test_전화번호_없을때_16바이트_전부_0(self):
        pkt = build_call_req(port=0, phone=None)
        phone_bytes = pkt[11:27]
        assert phone_bytes == b"\x00" * 16
        assert pkt[10] == 0  # phone_length = 0

    def test_노드id_항상_1(self):
        # Node ID는 항상 1 고정 (pkt[4:6] Little-endian)
        pkt = build_call_req(port=0, phone="1234")
        assert pkt[4:6] == b"\x01\x00"


# ─── MA_SE_CALL_RPT (11바이트) 파싱 ─────────────────────────────────────────

class TestParseCallRpt:
    def _make_call_rpt(self, result: int, port: int = 0, node_id: int = 1) -> bytes:
        """MA_SE_CALL_RPT 패킷 생성 헬퍼.

        실장비 확인 결과: MsgData = Port(1바이트) + ResultCode(1바이트)
        예) Port 0 OK → 00 11 / Port 1 OK → 01 11
        """
        # Header: 01 02 | 07 00 | NodeID(2,LE) | d0 | 02 00 | port(1) | result(1)
        return (
            b"\x01\x02"
            + b"\x07\x00"
            + node_id.to_bytes(2, "little")
            + b"\xd0"
            + b"\x02\x00"
            + bytes([port & 0xFF, result & 0xFF])
        )

    def test_OK_0x11_port0(self):
        pkt = self._make_call_rpt(0x11, port=0)
        assert parse_call_rpt(pkt) == CallResult.OK

    def test_OK_0x11_port1(self):
        pkt = self._make_call_rpt(0x11, port=1)
        assert parse_call_rpt(pkt) == CallResult.OK

    def test_NK_0x13(self):
        pkt = self._make_call_rpt(0x13)
        assert parse_call_rpt(pkt) == CallResult.NK

    def test_NK_0x16(self):
        pkt = self._make_call_rpt(0x16)
        assert parse_call_rpt(pkt) == CallResult.NK

    def test_BUSY_0x15(self):
        pkt = self._make_call_rpt(0x15)
        assert parse_call_rpt(pkt) == CallResult.BUSY

    def test_FAIL_0x23(self):
        pkt = self._make_call_rpt(0x23)
        assert parse_call_rpt(pkt) == CallResult.FAIL

    def test_알_수_없는_결과코드(self):
        pkt = self._make_call_rpt(0xFF)
        assert parse_call_rpt(pkt) == CallResult.FAIL

    def test_패킷_길이_부족(self):
        assert parse_call_rpt(b"\x01\x02") == CallResult.FAIL
