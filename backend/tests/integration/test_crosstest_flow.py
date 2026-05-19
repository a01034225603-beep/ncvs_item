import asyncio

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models import BacsDevice, SessionStatus, TestSession, User
from app.protocol.crosstest_proto import StubCrossTestProtocol
from app.services.crosstest.runner import PairRunner
from app.services.crosstest.scheduler import CrossTestScheduler
from app.services.session_service import create_session


@pytest.mark.asyncio
async def test_full_crosstest_run_completes_all_pairs(engine, db_session):
    user = User(username="u", password_hash="x")
    db_session.add(user)
    devices = [
        BacsDevice(name=f"b{i}", node_id=i, ip_address=f"127.0.0.{i+10}") for i in range(3)
    ]
    db_session.add_all(devices)
    await db_session.commit()
    for d in devices:
        await db_session.refresh(d)
    await db_session.refresh(user)

    ts = await create_session(
        db_session, user_id=user.id, device_ids=[d.id for d in devices]
    )

    factory = async_sessionmaker(engine, expire_on_commit=False)
    runner = PairRunner(StubCrossTestProtocol(speed_factor=300.0), factory, pair_timeout=5.0)
    scheduler = CrossTestScheduler(
        factory, runner, max_concurrent_pairs=4, dispatch_interval_ms=50
    )
    scheduler.start()
    scheduler.submit(ts.id)

    for _ in range(200):
        await asyncio.sleep(0.1)
        async with factory() as s:
            obj = await s.get(TestSession, ts.id)
            if obj.status == SessionStatus.completed:
                break
    else:
        pytest.fail("session did not complete in time")

    await scheduler.stop()

    async with factory() as s:
        obj = await s.get(TestSession, ts.id)
        assert obj.status == SessionStatus.completed
        assert obj.done_pairs == 6  # 3*2 directed pairs
        assert obj.ok_pairs == 6
