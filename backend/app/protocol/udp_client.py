"""
asyncio UDP heartbeat — uvloop 호환 구현
- loop.sock_sendto/sock_recvfrom 은 uvloop 에서 NotImplementedError 발생
- create_datagram_endpoint() 방식으로 교체 (uvloop 완전 지원)
"""
from __future__ import annotations

import asyncio

from app.protocol.messages import build_request, parse_response

# 수신 버퍼 크기
RECV_BUFFER: int = 1024


class _UdpProtocol(asyncio.DatagramProtocol):
    """단발성 UDP 요청/응답을 처리하는 프로토콜 핸들러."""

    def __init__(self, request: bytes, future: asyncio.Future) -> None:
        self._request = request
        self._future = future
        self.transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:  # type: ignore[override]
        self.transport = transport
        # 연결 직후 요청 패킷 전송
        self.transport.sendto(self._request)

    def datagram_received(self, data: bytes, addr: tuple) -> None:
        # 아직 완료되지 않은 경우에만 set
        if not self._future.done():
            self._future.set_result(data)

    def error_received(self, exc: Exception) -> None:
        if not self._future.done():
            self._future.set_exception(exc)

    def connection_lost(self, exc: Exception | None) -> None:
        if exc and not self._future.done():
            self._future.set_exception(exc)


async def heartbeat(host: str, port: int, *, timeout: float) -> None:
    """
    BACS 장비에 UDP 헬스체크 패킷을 전송하고 응답을 검증한다.
    uvloop 호환 (create_datagram_endpoint 기반).

    Raises:
        asyncio.TimeoutError — 타임아웃 (OFFLINE 판정)
        ValueError           — 응답 헤더 불일치 (OFFLINE 판정)
        OSError              — 네트워크 경로 없음 (OFFLINE 판정)
    """
    loop = asyncio.get_running_loop()
    future: asyncio.Future[bytes] = loop.create_future()

    # DatagramProtocol 기반으로 UDP 엔드포인트 생성 (uvloop 지원)
    transport, _ = await loop.create_datagram_endpoint(
        lambda: _UdpProtocol(build_request(), future),
        remote_addr=(host, port),
    )
    try:
        raw = await asyncio.wait_for(future, timeout=timeout)
    finally:
        transport.close()

    # 응답 패킷 유효성 검증
    if not parse_response(raw):
        raise ValueError(f"invalid response header: {raw[:9].hex()}")
