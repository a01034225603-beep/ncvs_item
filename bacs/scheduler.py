"""
bacs/scheduler.py
전체 장비 병렬 헬스체크
- run_all(devices) : asyncio.gather() 로 모든 장비를 동시에 체크
"""
from __future__ import annotations

import asyncio

from bacs.checker import check
from bacs.models import BacsDevice, CheckResult


async def run_all(devices: list[BacsDevice]) -> list[CheckResult]:
    """
    등록된 모든 장비를 asyncio.gather() 로 병렬 체크한다.

    Args:
        devices: 체크할 장비 목록

    Returns:
        list[CheckResult] — 각 장비의 헬스체크 결과 (입력 순서 보장)
    """
    if not devices:
        return []

    # 전체 장비를 동시에 체크 (병렬 실행)
    results: list[CheckResult] = await asyncio.gather(
        *[check(device) for device in devices]
    )
    return list(results)
