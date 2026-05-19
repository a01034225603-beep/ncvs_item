"""
loader.py 단위 테스트
TDD: 테스트 먼저 작성 → 실패 확인 → 구현 → 통과 확인
"""
import json
import pytest
from pathlib import Path

from bacs.loader import load_devices
from bacs.models import BacsDevice


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def devices_json(tmp_path: Path) -> Path:
    """정상 devices.json 임시 파일"""
    data = {
        "devices": [
            {"name": "BACS-AGW-001",   "ip": "192.168.1.10", "port": 7788, "network_type": "AGW"},
            {"name": "BACS-IPSEC-001", "ip": "192.168.2.10", "port": 7788, "network_type": "IPSEC"},
        ]
    }
    path = tmp_path / "devices.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.fixture
def devices_json_no_port(tmp_path: Path) -> Path:
    """port 필드 없는 devices.json"""
    data = {
        "devices": [
            {"name": "BACS-AGW-001", "ip": "192.168.1.10", "network_type": "AGW"},
        ]
    }
    path = tmp_path / "devices_no_port.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.fixture
def devices_json_empty(tmp_path: Path) -> Path:
    """devices 배열이 빈 devices.json"""
    data = {"devices": []}
    path = tmp_path / "devices_empty.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.fixture
def devices_json_invalid(tmp_path: Path) -> Path:
    """깨진 JSON 파일"""
    path = tmp_path / "devices_invalid.json"
    path.write_text("{ invalid json }", encoding="utf-8")
    return path


# ── 테스트 케이스 ──────────────────────────────────────────────────────────────

class TestLoadDevices:
    def test_load_devices_count(self, devices_json):
        """JSON 항목 수만큼 BacsDevice 반환"""
        devices = load_devices(devices_json)
        assert len(devices) == 2

    def test_load_devices_returns_list_of_bacs_device(self, devices_json):
        """반환 타입이 list[BacsDevice] 인지 확인"""
        devices = load_devices(devices_json)
        assert all(isinstance(d, BacsDevice) for d in devices)

    def test_load_devices_fields(self, devices_json):
        """각 필드가 정확히 매핑되는지 확인"""
        devices = load_devices(devices_json)
        first = devices[0]
        assert first.name         == "BACS-AGW-001"
        assert first.ip           == "192.168.1.10"
        assert first.port         == 7788
        assert first.network_type == "AGW"

    def test_load_devices_second_item(self, devices_json):
        """두 번째 항목도 올바르게 매핑되는지 확인"""
        devices = load_devices(devices_json)
        second = devices[1]
        assert second.name         == "BACS-IPSEC-001"
        assert second.network_type == "IPSEC"

    def test_load_devices_default_port(self, devices_json_no_port):
        """port 필드 없는 항목 → 기본값 7788 적용"""
        devices = load_devices(devices_json_no_port)
        assert devices[0].port == 7788

    def test_load_devices_empty(self, devices_json_empty):
        """devices 배열이 비어있으면 빈 리스트 반환"""
        devices = load_devices(devices_json_empty)
        assert devices == []

    def test_load_devices_file_not_found(self, tmp_path):
        """없는 파일 경로 → FileNotFoundError"""
        with pytest.raises(FileNotFoundError):
            load_devices(tmp_path / "not_exist.json")

    def test_load_devices_invalid_json(self, devices_json_invalid):
        """깨진 JSON → json.JSONDecodeError"""
        with pytest.raises(json.JSONDecodeError):
            load_devices(devices_json_invalid)

    def test_load_devices_accepts_str_path(self, devices_json):
        """Path 객체 대신 문자열 경로도 허용"""
        devices = load_devices(str(devices_json))
        assert len(devices) == 2
