import asyncio


class DeviceLocker:
    """In-process per-device locking with a global release notifier.

    Acquires the two device locks in a deterministic order (sorted by id) to
    avoid deadlocks. try_acquire_pair is non-blocking: it either takes both
    or releases any partial acquisition.
    """

    def __init__(self) -> None:
        self._locks: dict[int, asyncio.Lock] = {}
        self._owners: dict[int, int] = {}
        self._global_lock = asyncio.Lock()
        self._release_event = asyncio.Event()

    def _lock_for(self, bacs_id: int) -> asyncio.Lock:
        if bacs_id not in self._locks:
            self._locks[bacs_id] = asyncio.Lock()
        return self._locks[bacs_id]

    def is_locked(self, bacs_id: int) -> bool:
        lock = self._locks.get(bacs_id)
        return lock is not None and lock.locked()

    async def try_acquire_pair(self, a: int, b: int, *, session_id: int) -> bool:
        first, second = sorted([a, b])
        # Single global section per attempt — guarantees no two callers
        # interleave their lock checks and both succeed.
        async with self._global_lock:
            l1, l2 = self._lock_for(first), self._lock_for(second)
            if l1.locked() or l2.locked():
                return False
            await l1.acquire()
            await l2.acquire()
            self._owners[first] = session_id
            self._owners[second] = session_id
            return True

    async def release_pair(self, a: int, b: int) -> None:
        for bacs_id in (a, b):
            lock = self._locks.get(bacs_id)
            if lock and lock.locked():
                lock.release()
            self._owners.pop(bacs_id, None)
        self._release_event.set()
        self._release_event.clear()

    async def wait_for_release(self) -> None:
        await self._release_event.wait()

    def locked_devices(self) -> set[int]:
        return {bid for bid, lock in self._locks.items() if lock.locked()}
