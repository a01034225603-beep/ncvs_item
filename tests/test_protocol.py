"""
protocol.py 단위 테스트
TDD: 테스트 먼저 작성 → 실패 확인 → 구현 → 통과 확인
"""
import pytest
from bacs.protocol import build_request, parse_response


# ── build_request ────────────────────────────────────────────────────────────

class TestBuildRequest:
    def test_build_request_length(self):
        """요청 패킷은 정확히 9바이트여야 한다"""
        assert len(build_request()) == 9

    def test_build_request_bytes(self):
        """요청 패킷이 프로토콜 스펙과 정확히 일치해야 한다"""
        expected = bytes([0x01, 0x10, 0x05, 0x00, 0x00, 0x00, 0x12, 0x00, 0x00])
        assert build_request() == expected

    def test_build_request_returns_bytes(self):
        """반환 타입이 bytes 인지 확인"""
        assert isinstance(build_request(), bytes)


# ── parse_response ───────────────────────────────────────────────────────────

class TestParseResponse:
    # 유효한 응답 패킷 (헤더 9바이트 + alive 8바이트 = 13바이트)
    VALID_RESPONSE = bytes([
        0x01, 0x01, 0x0D, 0x00, 0x00, 0x00, 0x92, 0x08, 0x00,  # 헤더
        0x00, 0x00, 0x00, 0x00,                                   # alive (앞 4바이트)
    ])
    # alive 8바이트 완성 (총 13바이트)
    def _valid(self) -> bytes:
        """정상 17바이트 응답 패킷 (헤더 9 + alive 8)"""
        return bytes([
            0x01, 0x01, 0x0D, 0x00, 0x00, 0x00, 0x92, 0x08, 0x00,
            0xAB, 0xCD, 0xEF, 0x01, 0x00, 0x00, 0x00, 0x00,
        ])

    def test_parse_response_valid(self):
        """정상 13바이트 응답 → True"""
        assert parse_response(self._valid()) is True

    def test_parse_response_wrong_first_byte(self):
        """첫 번째 바이트가 다르면 → False"""
        data = bytearray(self._valid())
        data[0] = 0xFF
        assert parse_response(bytes(data)) is False

    def test_parse_response_wrong_header(self):
        """헤더 중간 바이트가 다르면 → False"""
        data = bytearray(self._valid())
        data[6] = 0x00  # 0x92 → 0x00
        assert parse_response(bytes(data)) is False

    def test_parse_response_too_short(self):
        """13바이트 미만 → False"""
        assert parse_response(self._valid()[:12]) is False

    def test_parse_response_too_long(self):
        """13바이트 초과 → False"""
        assert parse_response(self._valid() + b'\x00') is False

    def test_parse_response_empty(self):
        """빈 bytes → False"""
        assert parse_response(b'') is False

    def test_parse_response_wrong_type_returns_false(self):
        """쓰레기 데이터 → False"""
        assert parse_response(b'\xFF' * 13) is False
