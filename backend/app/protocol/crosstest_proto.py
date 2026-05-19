import asyncio
import random
from dataclasses import dataclass
from typing import Protocol

from app.models import BacsDevice


@dataclass(frozen=True)
class PairResult:
    ok: bool
    error_message: str | None = None


class CrossTestProtocol(Protocol):
    async def run_pair(
        self, src: BacsDevice, dst: BacsDevice, timeout: float
    ) -> PairResult: ...


class StubCrossTestProtocol:
    """Placeholder until BACS↔BACS call-test message format is finalized.

    Returns ok after 30s, fail after 60s, randomly weighted. Used in dev/tests
    to exercise the scheduler. Real implementation replaces this class.
    """

    def __init__(self, fail_rate: float = 0.0, speed_factor: float = 1.0) -> None:
        self.fail_rate = fail_rate
        self.speed_factor = speed_factor

    async def run_pair(
        self, src: BacsDevice, dst: BacsDevice, timeout: float
    ) -> PairResult:
        will_fail = random.random() < self.fail_rate
        wait = (60.0 if will_fail else 30.0) / self.speed_factor
        try:
            await asyncio.wait_for(asyncio.sleep(wait), timeout=timeout)
        except asyncio.TimeoutError:
            return PairResult(ok=False, error_message="pair timeout")
        if will_fail:
            return PairResult(ok=False, error_message="simulated failure")
        return PairResult(ok=True)
