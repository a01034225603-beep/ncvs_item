"""
UDP 헬스체크 실장비 통합 테스트
=============================
실제 BACS 장비가 연결된 환경에서만 실행합니다.

실행 방법:
    BACS_REAL_IP=192.168.1.10 pytest -m real_device -v -s

환경변수:
    BACS_REAL_IP          — 장비 IP 주소 (필수)
    BACS_REAL_UDP_PORT    — UDP 포트 (기본값 7788)
    BACS_REAL_TIMEOUT_SEC — 응답 대기 타임아웃 초 (기본값 5.0)
"""
from __future__ import annotations

import os

import pytest

from app.protocol.messages import RESPONSE_HEADER, RESPONSE_LENGTH, build_request
from app.protocol.udp_client import heartbeat

# ─── 환경변수 설정 ────────────────────────────────────────────────────────────
_REAL_IP      = os.environ.get("BACS_REAL_IP", "")
_REAL_PORT    = int(os.environ.get("BACS_REAL_UDP_PORT", "7788"))
_TIMEOUT_SEC  = float(os.environ.get("BACS_REAL_TIMEOUT_SEC", "5.0"))


def _skip_if_no_ip() -> None:
    """BACS_REAL_IP 미설정 시 테스트 스킵."""
    if not _REAL_IP:
        pytest.skip("BACS_REAL_IP 환경변수 미설정 → 실장비 없음으로 스킵")


# ─── UDP 헬스체크 테스트 ──────────────────────────────────────────────────────

@pytest.mark.real_device
async def test_udp_heartbeat_온라인_판정():
    """
    [STEP 1] UDP 헬스체크 기본 동작 — 응답 수신 후 ONLINE 판정.

    검증:
    - SE_MA_Connect_REQ (9바이트) 전송
    - MA_SE_Connect_RPT (17바이트) 수신
    - 헤더 9바이트 일치 → 예외 없이 완료 → ONLINE
    """
    _skip_if_no_ip()
    # 예외 없이 완료 = ONLINE 판정
    await heartbeat(_REAL_IP, _REAL_PORT, timeout=_TIMEOUT_SEC)
    print(f"\n[PASS] UDP ONLINE — {_REAL_IP}:{_REAL_PORT}")


@pytest.mark.real_device
async def test_udp_heartbeat_패킷_raw_검증():
    """
    [STEP 2] UDP 응답 패킷 raw 바이트 직접 검증 — 헤더 + 길이 확인.

    heartbeat()는 파싱 오류 시 ValueError를 raise하므로,
    여기서는 raw 소켓 레벨에서 한 번 더 패킷 내용을 직접 확인한다.
    alive 비트맵 8바이트도 출력하여 tcpdump 없이 내용 확인 가능.
    """
    _skip_if_no_ip()
    import asyncio

    loop = asyncio.get_running_loop()
    future: asyncio.Future[bytes] = loop.create_future()

    # _UdpProtocol에 접근하기 위해 직접 임포트
    from app.protocol.udp_client import _UdpProtocol

    transport, _ = await loop.create_datagram_endpoint(
        lambda: _UdpProtocol(build_request(), future),
        remote_addr=(_REAL_IP, _REAL_PORT),
    )
    try:
        raw = await asyncio.wait_for(future, timeout=_TIMEOUT_SEC)
    finally:
        transport.close()

    # ── 길이 검증 ──────────────────────────────────────────────────────────
    assert len(raw) == RESPONSE_LENGTH, (
        f"응답 패킷 길이 불일치: 기대={RESPONSE_LENGTH}, 실제={len(raw)}\n"
        f"raw hex: {raw.hex()}"
    )

    # ── 헤더 검증 ──────────────────────────────────────────────────────────
    assert raw[:9] == RESPONSE_HEADER, (
        f"응답 헤더 불일치:\n"
        f"  기대: {RESPONSE_HEADER.hex()}\n"
        f"  실제: {raw[:9].hex()}"
    )

    # ── alive 비트맵 출력 (8바이트, Little-endian) ─────────────────────────
    import struct
    alive = struct.unpack_from("<Q", raw, 9)[0]
    print(f"\n[PASS] UDP raw 검증 — {_REAL_IP}:{_REAL_PORT}")
    print(f"  응답 hex   : {raw.hex(' ')}")
    print(f"  alive 비트맵: 0x{alive:016X}")
    print(f"  (명세: BACS 기능 동작시 alive 값은 무시)")


@pytest.mark.real_device
async def test_udp_heartbeat_연속_3회():
    """
    [STEP 3] UDP 헬스체크 연속 3회 — 안정성 및 재현성 확인.

    동일 장비에 3회 연속 요청하여:
    - 매번 응답이 오는지
    - 응답 패킷 헤더가 일관적인지
    확인한다.
    """
    _skip_if_no_ip()
    for i in range(3):
        await heartbeat(_REAL_IP, _REAL_PORT, timeout=_TIMEOUT_SEC)
        print(f"\n  [{i+1}/3] ONLINE — {_REAL_IP}:{_REAL_PORT}")
    print("[PASS] 연속 3회 모두 ONLINE")
