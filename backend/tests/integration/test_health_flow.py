import pytest

from app.models import BacsDevice, DeviceHealth, HealthStatus
from app.services.health_service import HealthCheckService
from tests.simulator.fake_bacs import start_fake_bacs_udp


@pytest.mark.asyncio
async def test_health_check_marks_responding_device_ok(db_session):
    transport, _proto, port = await start_fake_bacs_udp()
    try:
        device = BacsDevice(name="t1", node_id=0, ip_address="127.0.0.1", udp_port=port)
        db_session.add(device)
        await db_session.commit()
        await db_session.refresh(device)

        svc = HealthCheckService(timeout=1.0, concurrency=4)
        await svc.run_once(db_session)

        health = await db_session.get(DeviceHealth, device.id)
        assert health is not None
        assert health.status == HealthStatus.ok
    finally:
        transport.close()


@pytest.mark.asyncio
async def test_health_check_marks_unreachable_device_fail(db_session):
    device = BacsDevice(name="dead", node_id=0, ip_address="127.0.0.1", udp_port=1)
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)

    svc = HealthCheckService(timeout=0.2, concurrency=4)
    await svc.run_once(db_session)

    health = await db_session.get(DeviceHealth, device.id)
    assert health.status == HealthStatus.fail
