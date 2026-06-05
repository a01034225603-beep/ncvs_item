import asyncio

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models import (
    BacsDevice,
    PairStatus,
    SessionStatus,
    TestSession,
    TestSessionPair,
    User,
)
from tests.simulator.stub_crosstest import StubCrossTestProtocol
from app.services.crosstest.runner import PairRunner
from app.services.crosstest.scheduler import CrossTestScheduler
from app.services.session_service import create_session_from_scenario


@pytest.mark.asyncio
async def test_overlapping_sessions_never_share_device_simultaneously(engine, db_session):
    user = User(username="u2", password_hash="x")
    db_session.add(user)
    devices = [
        BacsDevice(name=f"b{i}", node_id=i, ip_address=f"127.0.0.{i+50}") for i in range(4)
    ]
    db_session.add_all(devices)
    await db_session.commit()
    for d in devices:
        await db_session.refresh(d)
    await db_session.refresh(user)

    # Session A: devices 0,1  ; Session B: devices 1,2  (device 1 overlaps)
    # 양방향 2쌍 (0→1, 1→0) / (1→2, 2→1)
    sa = await create_session_from_scenario(
        db_session, user_id=user.id,
        sender_device_ids=[devices[0].id, devices[1].id],
        receiver_device_ids=[devices[0].id, devices[1].id],
    )
    sb = await create_session_from_scenario(
        db_session, user_id=user.id,
        sender_device_ids=[devices[1].id, devices[2].id],
        receiver_device_ids=[devices[1].id, devices[2].id],
    )

    factory = async_sessionmaker(engine, expire_on_commit=False)
    runner = PairRunner(StubCrossTestProtocol(speed_factor=300.0), factory, pair_timeout=5.0)
    scheduler = CrossTestScheduler(
        factory, runner, max_concurrent_pairs=8, dispatch_interval_ms=20
    )
    scheduler.start()
    scheduler.submit(sa.id)
    scheduler.submit(sb.id)

    # Poll: at no observation point may a device-1-touching pair be 'running' in both sessions
    # at the same time. Invariant: among all running pairs across both sessions, every
    # involved device is unique (total running pairs * 2 == unique device count).
    for _ in range(200):
        await asyncio.sleep(0.02)
        async with factory() as s:
            run_a = (await s.execute(
                select(TestSessionPair).where(
                    TestSessionPair.session_id == sa.id,
                    TestSessionPair.status == PairStatus.running,
                )
            )).scalars().all()
            run_b = (await s.execute(
                select(TestSessionPair).where(
                    TestSessionPair.session_id == sb.id,
                    TestSessionPair.status == PairStatus.running,
                )
            )).scalars().all()
            devices_in_flight: list[int] = []
            for row in list(run_a) + list(run_b):
                devices_in_flight.append(row.src_bacs_id)
                devices_in_flight.append(row.dst_bacs_id)
            assert len(set(devices_in_flight)) == len(devices_in_flight), (
                f"device appears in two running pairs simultaneously: {devices_in_flight}"
            )

    # Both sessions eventually complete
    for _ in range(200):
        await asyncio.sleep(0.05)
        async with factory() as s:
            a = await s.get(TestSession, sa.id)
            b = await s.get(TestSession, sb.id)
            if a.status == SessionStatus.completed and b.status == SessionStatus.completed:
                break
    else:
        pytest.fail("sessions did not complete in time")

    await scheduler.stop()
