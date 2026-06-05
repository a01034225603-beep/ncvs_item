"""
StubCrossTestProtocol — 스케줄러·락 로직 단위/통합 테스트 전용.

실제 BACS TCP 통신 없음.
프로덕션 코드(app/)에서 절대 import 금지.
"""
import asyncio
import random
from collections.abc import Callable

from app.models import BacsDevice
from app.protocol.crosstest_proto import EmitFn, PairResult


class StubCrossTestProtocol:
    """
    스케줄러·락 로직 검증에만 사용하는 테스트 전용 Stub.

    Args:
        fail_rate:    0.0 ~ 1.0, 이 확률로 PairResult(ok=False) 반환
        speed_factor: 대기 시간 배속 (300 → 300배 빠름, 테스트 속도 향상용)
    """

    def __init__(self, fail_rate: float = 0.0, speed_factor: float = 1.0) -> None:
        self.fail_rate = fail_rate
        self.speed_factor = speed_factor

    async def run_pair(
        self,
        src: BacsDevice,
        dst: BacsDevice,
        timeout: float,
        emit: EmitFn | None = None,  # 스텁에서는 패킷 이벤트 방출 없음
    ) -> PairResult:
        will_fail = random.random() < self.fail_rate
        # 정상: 30초, 실패: 60초 대기 (speed_factor 배속)
        wait = (60.0 if will_fail else 30.0) / self.speed_factor
        try:
            await asyncio.wait_for(asyncio.sleep(wait), timeout=timeout)
        except asyncio.TimeoutError:
            return PairResult(ok=False, error_message="pair timeout")
        if will_fail:
            return PairResult(ok=False, error_message="simulated failure")
        return PairResult(ok=True)
