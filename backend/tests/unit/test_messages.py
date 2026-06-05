"""
test_messages.py
build_request / parse_response 단위 테스트
(tcpdump 실측 기준: 요청 9바이트 / 응답 17바이트)
"""
import pytest

from app.protocol.messages import build_request, parse_response

# 테스트용 정상 응답 패킷 (17바이트)
VALID_RESPONSE = bytes([
    0x01, 0x01,              # 패킷 타입
    0x0D, 0x00,              # 길이
    0x00, 0x00,              # 시퀀스
    0x92,                    # 커맨드
    0x08, 0x00,              # 예약
    0xFF, 0x00, 0x00, 0x00,  # alive (8바이트)
    0x00, 0x00, 0x00, 0x00,
])


def test_build_request_length():
    """요청 패킷은 9바이트여야 한다."""
    assert len(build_request()) == 9


def test_build_request_bytes():
    """요청 패킷이 프로토콜 스펙과 정확히 일치해야 한다."""
    expected = bytes([0x01, 0x10, 0x05, 0x00, 0x00, 0x00, 0x12, 0x00, 0x00])
    assert build_request() == expected


def test_parse_response_valid():
    """정상 응답(17바이트, 헤더 일치) → True"""
    assert parse_response(VALID_RESPONSE) is True


def test_parse_response_too_short():
    """길이 부족 → False"""
    assert parse_response(VALID_RESPONSE[:13]) is False


def test_parse_response_too_long():
    """길이 초과 → False"""
    assert parse_response(VALID_RESPONSE + b"\x00") is False


def test_parse_response_wrong_header():
    """헤더 불일치 → False"""
    bad = bytearray(VALID_RESPONSE)
    bad[0] = 0xFF  # 첫 바이트 오염
    assert parse_response(bytes(bad)) is False


def test_parse_response_empty():
    """빈 데이터 → False"""
    assert parse_response(b"") is False
