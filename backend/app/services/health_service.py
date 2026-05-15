import asyncio
from datetime import datetime

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
                return device.id, HealthStatus.ok, None
            except asyncio.TimeoutError:
                return device.id, HealthStatus.fail, "timeout"
            except Exception as exc:  # noqa: BLE001
                return device.id, HealthStatus.fail, str(exc)[:255]

    async def run_once(self, session: AsyncSession) -> None:
        devices = await device_repo.list_enabled(session)
        logger.info("health_check.tick devices={}", len(devices))
        results = await asyncio.gather(*(self._check_one(d) for d in devices))
        now = datetime.utcnow()
        for bacs_id, status, error in results:
            await health_repo.upsert(
                session, bacs_id=bacs_id, status=status, checked_at=now, error=error
            )
        await session.commit()
