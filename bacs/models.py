"""
bacs/models.py
BACS UDP 헬스체크 데이터 모델 정의
- HealthStatus : 장비 상태 Enum
- BacsDevice   : 장비 정보 (devices.json 역직렬화 호환)
- CheckResult  : 단일 헬스체크 결과 VO
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class HealthStatus(str, Enum):
    """장비 헬스 상태 (str 서브클래스 → JSON 직렬화 호환)"""
    ONLINE  = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


@dataclass
class BacsDevice:
    """
    BACS 장비 정보.
    devices.json 의 항목을 그대로 언패킹하여 생성 가능.
    예) BacsDevice(**json_item)
    """
    name:         str           # 장비 식별자 (예: "BACS-AGW-001")
    ip:           str           # IPv4 주소
    network_type: str           # 네트워크 유형 (예: "AGW", "IPSEC")
    port:         int = 7788    # UDP 포트 (기본값 7788 고정)


@dataclass
class CheckResult:
    """
    단일 장비 헬스체크 결과 Value Object.
    checker.py 가 생성하여 scheduler.py 로 전달.
    """
    device:       BacsDevice           # 체크 대상 장비
    status:       HealthStatus         # 판정 결과
    latency_ms:   float | None         # 응답 왕복시간 (ms), 타임아웃 시 None
    checked_at:   datetime             # 체크 시각 (반드시 UTC aware)

    # 디버그용 원본 응답 패킷 (기본값 None)
    raw_response: bytes | None = field(default=None)
