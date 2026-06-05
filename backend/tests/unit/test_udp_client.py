"""
test_udp_client.py
heartbeat() 단위 테스트 — create_datagram_endpoint 기반 구현 (uvloop 호환)
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 정상 응답 패킷 (17바이트)
VALID_RESPONSE = bytes([
    0x01, 0x01, 0x0D, 0x00, 0x00, 0x00, 0x92, 0x08, 0x00,
    0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
])

# 헤더 불일치 응답 패킷 (17바이트, 첫 바이트 오염)
BAD_RESPONSE = bytes([0xFF]) + VALID_RESPONSE[1:]


def _make_endpoint_mock(response: bytes | None = None, raise_exc: Exception | None = None):
    """
    loop.create_datagram_endpoint 를 mock한다.
    - _UdpProtocol 생성자에 주입된 future 를 즉시 resolve/reject 한다.
    """
    async def fake_create_datagram_endpoint(protocol_factory, *, remote_addr):
        transport = MagicMock()
        transport.close = MagicMock()
        proto = protocol_factory()
        proto.connection_made(transport)  # connection_made 호출 (sendto 트리거)
        # future 를 직접 조작
        if raise_exc is not None:
            proto._future.set_exception(raise_exc)
        elif response is not None:
            proto._future.set_result(response)
        return transport, proto

    return fake_create_datagram_endpoint


@pytest.mark.asyncio
async def test_heartbeat_online():
    """정상 응답 수신 → 예외 없이 리턴 (ONLINE 판정)"""
    loop = asyncio.get_event_loop()
    with patch.object(loop, "create_datagram_endpoint",
                      side_effect=_make_endpoint_mock(response=VALID_RESPONSE)):
        from app.protocol.udp_client import heartbeat
        await heartbeat("192.168.1.10", 7788, timeout=5.0)  # 예외 없으면 성공


@pytest.mark.asyncio
async def test_heartbeat_timeout():
    """타임아웃 발생 → asyncio.TimeoutError (OFFLINE 판정)"""
    async def slow_endpoint(protocol_factory, *, remote_addr):
        """future 가 절대 resolve 되지 않는 엔드포인트 (timeout 유도)"""
        transport = MagicMock()
        transport.close = MagicMock()
        proto = protocol_factory()
        proto.connection_made(transport)
        # future 를 resolve 하지 않음 → wait_for 가 TimeoutError 발생
        return transport, proto

    loop = asyncio.get_event_loop()
    with patch.object(loop, "create_datagram_endpoint", side_effect=slow_endpoint):
        from app.protocol.udp_client import heartbeat
        with pytest.raises(asyncio.TimeoutError):
            await heartbeat("192.168.1.10", 7788, timeout=0.01)


@pytest.mark.asyncio
async def test_heartbeat_bad_response():
    """헤더 불일치 응답 → ValueError (OFFLINE 판정)"""
    loop = asyncio.get_event_loop()
    with patch.object(loop, "create_datagram_endpoint",
                      side_effect=_make_endpoint_mock(response=BAD_RESPONSE)):
        from app.protocol.udp_client import heartbeat
        with pytest.raises(ValueError):
            await heartbeat("192.168.1.10", 7788, timeout=5.0)


@pytest.mark.asyncio
async def test_heartbeat_oserror():
    """네트워크 경로 없음 → OSError (OFFLINE 판정)"""
    loop = asyncio.get_event_loop()
    with patch.object(loop, "create_datagram_endpoint",
                      side_effect=_make_endpoint_mock(raise_exc=OSError(51, "Network is unreachable"))):
        from app.protocol.udp_client import heartbeat
        with pytest.raises(OSError):
            await heartbeat("192.168.1.10", 7788, timeout=5.0)
