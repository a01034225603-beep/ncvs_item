"""
models.py 단위 테스트
TDD: 테스트 먼저 작성 → 실패 확인 → 구현 → 통과 확인
"""
import pytest
from datetime import datetime, timezone
from bacs.models import HealthStatus, BacsDevice, CheckResult


# ── HealthStatus ────────────────────────────────────────────────────────────

class TestHealthStatus:
    def test_health_status_values(self):
        """세 가지 상태값이 정확한 문자열인지 확인"""
        assert HealthStatus.ONLINE  == "online"
        assert HealthStatus.OFFLINE == "offline"
        assert HealthStatus.UNKNOWN == "unknown"

    def test_health_status_is_str(self):
        """str 서브클래스 여부 확인 (JSON 직렬화 호환)"""
        assert isinstance(HealthStatus.ONLINE, str)


# ── BacsDevice ───────────────────────────────────────────────────────────────

class TestBacsDevice:
    def test_bacs_device_creation(self):
        """정상 필드로 BacsDevice 생성"""
        device = BacsDevice(name="BACS-AGW-001", ip="192.168.1.10", network_type="AGW")
        assert device.name         == "BACS-AGW-001"
        assert device.ip           == "192.168.1.10"
        assert device.network_type == "AGW"

    def test_bacs_device_default_port(self):
        """port 생략 시 기본값 7788 적용"""
        device = BacsDevice(name="BACS-AGW-001", ip="192.168.1.10", network_type="AGW")
        assert device.port == 7788

    def test_bacs_device_custom_port(self):
        """port 직접 지정 시 해당 값 사용"""
        device = BacsDevice(name="TEST", ip="10.0.0.1", port=9999, network_type="AGW")
        assert device.port == 9999

    def test_bacs_device_from_dict(self):
        """devices.json 한 항목을 그대로 언패킹하여 생성 가능한지 확인"""
        raw = {
            "name": "BACS-IPSEC-001",
            "ip": "192.168.2.10",
            "port": 7788,
            "network_type": "IPSEC",
        }
        device = BacsDevice(**raw)
        assert device.name == "BACS-IPSEC-001"
        assert device.network_type == "IPSEC"


# ── CheckResult ──────────────────────────────────────────────────────────────

class TestCheckResult:
    def _make_device(self) -> BacsDevice:
        return BacsDevice(name="BACS-AGW-001", ip="192.168.1.10", network_type="AGW")

    def test_check_result_online(self):
        """ONLINE 상태와 latency 값이 그대로 보존되는지 확인"""
        device = self._make_device()
        result = CheckResult(
            device=device,
            status=HealthStatus.ONLINE,
            latency_ms=12.5,
            checked_at=datetime.now(timezone.utc),
        )
        assert result.status     == HealthStatus.ONLINE
        assert result.latency_ms == 12.5

    def test_check_result_offline_timeout(self):
        """타임아웃(OFFLINE) 시 latency_ms 는 None"""
        device = self._make_device()
        result = CheckResult(
            device=device,
            status=HealthStatus.OFFLINE,
            latency_ms=None,
            checked_at=datetime.now(timezone.utc),
        )
        assert result.status     == HealthStatus.OFFLINE
        assert result.latency_ms is None

    def test_check_result_timestamp_utc(self):
        """checked_at 이 UTC aware datetime 인지 확인"""
        device = self._make_device()
        now = datetime.now(timezone.utc)
        result = CheckResult(
            device=device,
            status=HealthStatus.UNKNOWN,
            latency_ms=None,
            checked_at=now,
        )
        assert result.checked_at.tzinfo is not None
        assert result.checked_at.tzinfo == timezone.utc

    def test_check_result_raw_response_default_none(self):
        """raw_response 생략 시 기본값 None"""
        device = self._make_device()
        result = CheckResult(
            device=device,
            status=HealthStatus.ONLINE,
            latency_ms=5.0,
            checked_at=datetime.now(timezone.utc),
        )
        assert result.raw_response is None

    def test_check_result_raw_response_stored(self):
        """실제 응답 패킷 바이트가 그대로 저장되는지 확인"""
        device = self._make_device()
        raw = bytes.fromhex("01010D0000009208000000000000")
        result = CheckResult(
            device=device,
            status=HealthStatus.ONLINE,
            latency_ms=3.2,
            checked_at=datetime.now(timezone.utc),
            raw_response=raw,
        )
        assert result.raw_response == raw
