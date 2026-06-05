"""
bacs/protocol.py 기반으로 교체
- tcpdump 실측으로 확정된 패킷 구조 사용 (요청 9바이트 / 응답 17바이트)
"""

# 요청 패킷 SE_MA_Connect_REQ (9바이트 고정)
REQUEST_PACKET: bytes = bytes([
    0x01, 0x10,  # 패킷 타입
    0x05, 0x00,  # 길이
    0x00, 0x00,  # 시퀀스
    0x12,        # 커맨드
    0x00, 0x00,  # 예약
])

# 응답 패킷 MA_SE_Connect_RPT 헤더 (앞 9바이트)
RESPONSE_HEADER: bytes = bytes([
    0x01, 0x01,  # 패킷 타입
    0x0D, 0x00,  # 길이
    0x00, 0x00,  # 시퀀스
    0x92,        # 커맨드
    0x08, 0x00,  # 예약
])

# 응답 전체 길이: Type(2) + Length(2) + Data(13) = 17바이트
RESPONSE_LENGTH: int = 17


def build_request() -> bytes:
    """BACS 장비로 전송할 요청 패킷(9바이트)을 반환한다."""
    return REQUEST_PACKET


def parse_response(data: bytes) -> bool:
    """
    수신 데이터가 유효한 응답 패킷인지 검증한다.

    Returns:
        True  — 길이 17바이트 + 헤더 9바이트 일치 (ONLINE)
        False — 불일치 (OFFLINE)
    """
    # 길이 검증 먼저
    if len(data) != RESPONSE_LENGTH:
        return False
    # 헤더 9바이트 일치 여부 확인
    return data[:9] == RESPONSE_HEADER
