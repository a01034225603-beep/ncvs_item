"""
repositories 패키지 - DB CRUD 함수 모음

각 모듈은 특정 테이블에 대한 비동기 DB 접근 함수를 제공한다.
모든 함수는 AsyncSession 을 인자로 받고 commit() 은 호출자가 책임진다.
"""
from app.repositories import (
    device_repo,
    health_repo,
    lock_repo,
    pair_repo,
    scenario_repo,
    session_repo,
    user_repo,
)

__all__ = [
    "device_repo",
    "health_repo",
    "lock_repo",
    "pair_repo",
    "scenario_repo",
    "session_repo",
    "user_repo",
]
