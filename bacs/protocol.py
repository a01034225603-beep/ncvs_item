"""
bacs/protocol.py
BACS UDP 패킷 빌드 및 파싱
- build_request  : 요청 패킷(9바이트) 생성
- parse_response : 응답 패킷(13바이트) 유효성 검증
"""

# 요청 패킷 SE_MA_Connect_REQ (9바이트, 고정값)
REQUEST_PACKET: bytes = bytes([
    0x01, 0x10,              # 패킷 타입
    0x05, 0x00,              # 길이
    0x00, 0x00,              # 시퀀스
    0x12,                    # 커맨드
    0x00, 0x00,              # 예약
])

# 응답 패킷 MA_SE_Connect_RPT 헤더 (앞 9바이트)
RESPONSE_HEADER: bytes = bytes([
    0x01, 0x01,              # 패킷 타입
    0x0D, 0x00,              # 길이
    0x00, 0x00,              # 시퀀스
    0x92,                    # 커맨드
    0x08, 0x00,              # 예약
])

# 응답 패킷 전체 길이
# Type(2) + Length(2) + Data(13) = 17바이트
# 0D 00 = 13은 Data 길이를 의미, 전체 패킷은 17바이트
RESPONSE_LENGTH: int = 17


def build_request() -> bytes:
    """
    BACS 장비로 전송할 요청 패킷을 반환한다.
    SE_MA_Connect_REQ : 9바이트 고정 패킷
    """
    return REQUEST_PACKET


def parse_response(data: bytes) -> bool:
    """
    수신한 데이터가 유효한 응답 패킷인지 검증한다.
    MA_SE_Connect_RPT : 13바이트, 앞 9바이트 헤더 일치 여부 확인

    Returns:
        True  — 길이 13바이트 + 헤더 일치 (ONLINE 판정 가능)
        False — 길이 불일치 또는 헤더 불일치 (OFFLINE 판정)
    """
    # 길이 검증 먼저
    if len(data) != RESPONSE_LENGTH:
        return False

    # 헤더 9바이트 일치 여부 확인
    return data[:9] == RESPONSE_HEADER
