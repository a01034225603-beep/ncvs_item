"""
bacs/checker.py
BACS 장비 단일 UDP 헬스체크
- check(device) : 장비 한 대에 UDP 패킷 전송 후 ONLINE/OFFLINE 판정
"""
from __future__ import annotations

import asyncio
import socket
import time
from datetime import datetime, timezone

from bacs.models import BacsDevice, CheckResult, HealthStatus
from bacs.protocol import build_request, parse_response

# UDP 응답 대기 타임아웃 (초)
TIMEOUT_SEC: float = 5.0

# 수신 버퍼 크기 (bytes)
RECV_BUFFER: int = 1024


async def check(device: BacsDevice) -> CheckResult:
    """
    장비 한 대에 UDP 패킷을 전송하고 응답으로 상태를 판정한다.

    판정 규칙:
        응답 수신 + 헤더 일치 → ONLINE
        타임아웃              → OFFLINE (latency_ms=None)
        응답 수신 + 헤더 불일치 → OFFLINE (latency_ms=None)

    Returns:
        CheckResult — 판정 결과 VO
    """
    loop = asyncio.get_event_loop()
    packet = build_request()
    checked_at = datetime.now(timezone.utc)

    # 비동기 UDP 소켓 생성
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(False)

    try:
        try:
            # 요청 패킷 전송 및 응답 수신 시간 측정
            send_time = time.monotonic()
            await loop.sock_sendto(sock, packet, (device.ip, device.port))
            # 타임아웃 내 응답 대기
            raw, _ = await asyncio.wait_for(
                loop.sock_recvfrom(sock, RECV_BUFFER),
                timeout=TIMEOUT_SEC,
            )
            recv_time = time.monotonic()
            latency_ms = (recv_time - send_time) * 1000

            # 응답 패킷 유효성 검증
            if parse_response(raw):
                return CheckResult(
                    device=device,
                    status=HealthStatus.ONLINE,
                    latency_ms=latency_ms,
                    checked_at=checked_at,
                    raw_response=raw,
                )
            else:
                # 헤더 불일치 → OFFLINE
                return CheckResult(
                    device=device,
                    status=HealthStatus.OFFLINE,
                    latency_ms=None,
                    checked_at=checked_at,
                    raw_response=raw,
                )

        except asyncio.TimeoutError:
            # 타임아웃 → OFFLINE
            return CheckResult(
                device=device,
                status=HealthStatus.OFFLINE,
                latency_ms=None,
                checked_at=checked_at,
                raw_response=None,
            )

        except OSError:
            # 네트워크 경로 없음 (예: 로컬 네트워크 미접속 시 EINVAL 51) → OFFLINE
            return CheckResult(
                device=device,
                status=HealthStatus.OFFLINE,
                latency_ms=None,
                checked_at=checked_at,
                raw_response=None,
            )

    finally:
        # 소켓 반드시 닫기 (leak 방지)
        sock.close()
