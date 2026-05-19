"""
checker.py 단위 테스트 + 통합 테스트
TDD: 테스트 먼저 작성 → 실패 확인 → 구현 → 통과 확인

단위 테스트  : mock 소켓 사용, 네트워크 불필요 (항상 실행)
통합 테스트  : 실제 BACS 장비 필요 (pytest -m integration)
"""
import asyncio
import socket
from datetime import timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bacs.models import BacsDevice, CheckResult, HealthStatus


# ── 공통 픽스처 ──────────────────────────────────────────────────────────────

@pytest.fixture
def device() -> BacsDevice:
    return BacsDevice(name="BACS-AGW-001", ip="192.168.1.10", network_type="AGW")


# 정상 응답 패킷 (17바이트 = 헤더 9 + alive 8)
VALID_RESPONSE = bytes([
    0x01, 0x01, 0x0D, 0x00, 0x00, 0x00, 0x92, 0x08, 0x00,
    0xAB, 0xCD, 0xEF, 0x01, 0x00, 0x00, 0x00, 0x00,
])

# 잘못된 응답 패킷 (17바이트지만 헤더 불일치)
BAD_RESPONSE = bytes([0xFF] * 17)


# ── 단위 테스트 (mock) ────────────────────────────────────────────────────────

class TestCheckUnit:
    async def _run_check(self, device, recv_side_effect):
        """
        소켓의 recv 동작을 mock 으로 교체하여 check() 실행.
        recv_side_effect: 반환값(bytes) 또는 예외 클래스
        """
        from bacs.checker import check

        mock_sock = MagicMock(spec=socket.socket)

        with patch("bacs.checker.socket.socket", return_value=mock_sock):
            loop = asyncio.get_event_loop()

            # sendto 는 그냥 통과
            loop.sock_sendto = AsyncMock(return_value=None)

            if isinstance(recv_side_effect, type) and issubclass(recv_side_effect, Exception):
                loop.sock_recvfrom = AsyncMock(side_effect=recv_side_effect())
            else:
                loop.sock_recvfrom = AsyncMock(return_value=(recv_side_effect, ("192.168.1.10", 7788)))

            with patch("asyncio.get_event_loop", return_value=loop):
                return await check(device)

    async def test_check_online(self, device):
        """정상 응답 수신 → ONLINE, latency_ms 값 있음"""
        result = await self._run_check(device, VALID_RESPONSE)
        assert result.status == HealthStatus.ONLINE
        assert result.latency_ms is not None
        assert result.latency_ms >= 0

    async def test_check_offline_timeout(self, device):
        """타임아웃 발생 → OFFLINE, latency_ms=None"""
        result = await self._run_check(device, asyncio.TimeoutError)
        assert result.status == HealthStatus.OFFLINE
        assert result.latency_ms is None

    async def test_check_offline_bad_response(self, device):
        """헤더 불일치 응답 → OFFLINE, latency_ms=None"""
        result = await self._run_check(device, BAD_RESPONSE)
        assert result.status == HealthStatus.OFFLINE
        assert result.latency_ms is None

    async def test_check_result_has_device(self, device):
        """반환된 CheckResult.device 가 입력 장비와 동일"""
        result = await self._run_check(device, VALID_RESPONSE)
        assert result.device == device

    async def test_check_result_checked_at_utc(self, device):
        """checked_at 이 UTC aware datetime"""
        result = await self._run_check(device, VALID_RESPONSE)
        assert result.checked_at.tzinfo is not None
        assert result.checked_at.tzinfo == timezone.utc

    async def test_check_result_raw_response_stored(self, device):
        """ONLINE 시 raw_response 에 수신 패킷 저장"""
        result = await self._run_check(device, VALID_RESPONSE)
        assert result.raw_response == VALID_RESPONSE

    async def test_check_result_raw_response_none_on_timeout(self, device):
        """타임아웃 시 raw_response 는 None"""
        result = await self._run_check(device, asyncio.TimeoutError)
        assert result.raw_response is None


# ── 통합 테스트 (실제 장비 필요) ─────────────────────────────────────────────

@pytest.mark.integration
class TestCheckIntegration:
    """
    실행 방법: 로컬 네트워크 진입 후
    pytest -m integration -v
    """

    async def test_check_real_device_agw(self):
        """AGW 장비 실제 UDP 헬스체크 → ONLINE"""
        from bacs.checker import check
        device = BacsDevice(name="BACS-AGW-001", ip="192.168.1.10", network_type="AGW")
        result = await check(device)
        assert result.status == HealthStatus.ONLINE
        assert result.latency_ms is not None

    async def test_check_real_device_ipsec(self):
        """IPSEC 장비 실제 UDP 헬스체크 → ONLINE"""
        from bacs.checker import check
        device = BacsDevice(name="BACS-IPSEC-001", ip="192.168.2.10", network_type="IPSEC")
        result = await check(device)
        assert result.status == HealthStatus.ONLINE
        assert result.latency_ms is not None
