"""
프로젝트 전체에서 사용하는 모든 ORM 모델을 단일 지점에서 import 할 수 있도록 직렬화한 파일.

테이블 구조:
  bacs_devices     — BACS 장비 목록
  health_records   — 장비별 UDP 헬스체크 최신 상태
  device_locks     — 호출시험 실행 중 장비 잠금 테이블
  scenarios        — 호출시험 시나리오 (발신/착신 장비 조합)
  test_sessions    — 호출시험 세션 (실행 단위)
  test_session_pairs — 세션 안 마닥 (A단말 → B단말 1쌍)
  pair_latest_result — 페어별 가장 최근 호출시험 결과
  users            — 관리자 계정
"""
from app.models.bacs import BacsDevice
from app.models.health import DeviceHealth, HealthStatus
from app.models.lock import DeviceLock
from app.models.pair import (
    PairLatestResult,
    PairLatestStatus,
    PairStatus,
    TestSessionPair,
)
from app.models.scenario import Scenario
from app.models.session import SessionStatus, TestSession
from app.models.user import User

__all__ = [
    "User",
    "BacsDevice",
    "DeviceHealth",
    "HealthStatus",
    "TestSession",
    "SessionStatus",
    "TestSessionPair",
    "PairStatus",
    "PairLatestResult",
    "PairLatestStatus",
    "DeviceLock",
    "Scenario",
]
