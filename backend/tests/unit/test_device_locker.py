import asyncio

import pytest

from app.services.crosstest.device_locker import DeviceLocker


@pytest.mark.asyncio
async def test_acquire_pair_succeeds_when_both_free():
    locker = DeviceLocker()
    assert await locker.try_acquire_pair(1, 2, session_id=10) is True
    assert locker.is_locked(1) and locker.is_locked(2)


@pytest.mark.asyncio
async def test_acquire_pair_fails_when_one_locked():
    locker = DeviceLocker()
    await locker.try_acquire_pair(1, 2, session_id=10)
    assert await locker.try_acquire_pair(2, 3, session_id=11) is False
    # device 3 must NOT be left locked
    assert not locker.is_locked(3)


@pytest.mark.asyncio
async def test_release_unblocks_waiters():
    locker = DeviceLocker()
    await locker.try_acquire_pair(1, 2, session_id=10)
    waiter = asyncio.create_task(locker.wait_for_release())
    await asyncio.sleep(0)
    assert not waiter.done()
    await locker.release_pair(1, 2)
    await asyncio.wait_for(waiter, timeout=0.5)


@pytest.mark.asyncio
async def test_acquire_pair_always_orders_lock_acquisition():
    """Ordered acquisition prevents deadlock between (1,2) and (2,1)."""
    locker = DeviceLocker()
    a = locker.try_acquire_pair(1, 2, session_id=10)
    b = locker.try_acquire_pair(2, 1, session_id=11)
    results = await asyncio.gather(a, b)
    # Exactly one must win, never both, never neither (no deadlock).
    assert sum(results) == 1
