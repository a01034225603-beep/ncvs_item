"""
scheduler.py 단위 테스트
TDD: 테스트 먼저 작성 → 실패 확인 → 구현 → 통과 확인

모든 장비를 asyncio.gather() 로 병렬 체크하는 로직 검증
"""
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

from bacs.models import BacsDevice, CheckResult, HealthStatus
from bacs.scheduler import run_all


# ── 공통 픽스처 ──────────────────────────────────────────────────────────────

@pytest.fixture
def devices() -> list[BacsDevice]:
    return [
        BacsDevice(name="BACS-AGW-001",   ip="192.168.1.10", network_type="AGW"),
        BacsDevice(name="BACS-IPSEC-001", ip="192.168.2.10", network_type="IPSEC"),
    ]


def _make_result(device: BacsDevice, status: HealthStatus) -> CheckResult:
    return CheckResult(
        device=device,
        status=status,
        latency_ms=10.0 if status == HealthStatus.ONLINE else None,
        checked_at=datetime.now(timezone.utc),
    )


# ── 테스트 케이스 ─────────────────────────────────────────────────────────────

class TestRunAll:
    async def test_run_all_returns_all_results(self, devices):
        """장비 수만큼 CheckResult 반환"""
        mock_results = [_make_result(d, HealthStatus.ONLINE) for d in devices]

        with patch("bacs.scheduler.check", side_effect=AsyncMock(side_effect=mock_results)):
            results = await run_all(devices)

        assert len(results) == 2

    async def test_run_all_returns_check_result_type(self, devices):
        """반환값이 list[CheckResult] 인지 확인"""
        mock_results = [_make_result(d, HealthStatus.ONLINE) for d in devices]

        with patch("bacs.scheduler.check", side_effect=AsyncMock(side_effect=mock_results)):
            results = await run_all(devices)

        assert all(isinstance(r, CheckResult) for r in results)

    async def test_run_all_parallel_execution(self, devices):
        """check() 가 장비 수만큼 호출되는지 확인 (병렬 실행 검증)"""
        mock_results = [_make_result(d, HealthStatus.ONLINE) for d in devices]
        mock_check = AsyncMock(side_effect=mock_results)

        with patch("bacs.scheduler.check", mock_check):
            await run_all(devices)

        assert mock_check.call_count == len(devices)

    async def test_run_all_passes_correct_device(self, devices):
        """각 check() 호출에 올바른 장비가 전달되는지 확인"""
        mock_results = [_make_result(d, HealthStatus.ONLINE) for d in devices]
        mock_check = AsyncMock(side_effect=mock_results)

        with patch("bacs.scheduler.check", mock_check):
            await run_all(devices)

        called_devices = [call.args[0] for call in mock_check.call_args_list]
        assert called_devices == devices

    async def test_run_all_mixed_status(self, devices):
        """일부 ONLINE, 일부 OFFLINE — 결과가 섞여도 모두 반환"""
        mock_results = [
            _make_result(devices[0], HealthStatus.ONLINE),
            _make_result(devices[1], HealthStatus.OFFLINE),
        ]

        with patch("bacs.scheduler.check", side_effect=AsyncMock(side_effect=mock_results)):
            results = await run_all(devices)

        statuses = {r.device.name: r.status for r in results}
        assert statuses["BACS-AGW-001"]   == HealthStatus.ONLINE
        assert statuses["BACS-IPSEC-001"] == HealthStatus.OFFLINE

    async def test_run_all_empty_devices(self):
        """빈 장비 리스트 → 빈 결과 반환"""
        results = await run_all([])
        assert results == []
