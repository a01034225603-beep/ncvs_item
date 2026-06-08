"""
UDP 헬스체크 서비스 모듈.

역할:
  - DB 에서 enabled=True 인 BACS 장비 목록을 가져와 UDP heartbeat 상태를 주기적으로 확인한다.
  - ONLINE(응답 정상) / OFFLINE(타임아웃/네트워크 에러) 상태를 health_records 테이블에 upsert 한다.
  - main.py 에서 APScheduler 로 60초 주기로 등록되는 주기 작업이다.
  - concurrency: asyncio.Semaphore 로 적얹 동시 UDP 쾼리 수 제한 (config: HEALTH_CHECK_CONCURRENCY).
"""
import asyncio
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BacsDevice, HealthStatus
from app.protocol.udp_client import heartbeat
from app.repositories import device_repo, health_repo


class HealthCheckService:
    def __init__(self, *, timeout: float, concurrency: int) -> None:
        self.timeout = timeout
        self.semaphore = asyncio.Semaphore(concurrency)

    async def _check_one(self, device: BacsDevice) -> tuple[int, HealthStatus, str | None]:
        async with self.semaphore:
            try:
                await heartbeat(device.ip_address, device.udp_port, timeout=self.timeout)
                logger.info("health_check.online id={} ip={}", device.id, device.ip_address)
                return device.id, HealthStatus.online, None
            except asyncio.TimeoutError:
                # 타임아웃 → OFFLINE
                logger.info("health_check.offline id={} ip={} reason=timeout", device.id, device.ip_address)
                return device.id, HealthStatus.offline, "timeout"
            except OSError as exc:
                # 네트워크 경로 없음 → OFFLINE
                logger.info("health_check.offline id={} ip={} reason=os_error err={}", device.id, device.ip_address, exc)
                return device.id, HealthStatus.offline, f"network error: {exc}"
            except Exception as exc:  # noqa: BLE001
                logger.warning("health_check.offline id={} ip={} type={} err={}", device.id, device.ip_address, type(exc).__name__, exc)
                return device.id, HealthStatus.offline, str(exc)[:255]

    async def run_once(self, session: AsyncSession) -> None:
        devices = await device_repo.list_enabled(session)
        logger.info("health_check.tick devices={}", len(devices))
        results = await asyncio.gather(*(self._check_one(d) for d in devices))
        now = datetime.now(timezone.utc)
        for bacs_id, status, error in results:
            await health_repo.upsert(
                session, bacs_id=bacs_id, status=status, checked_at=now, error=error
            )
        await session.commit()
