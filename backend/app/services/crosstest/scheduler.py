import asyncio

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import BacsDevice, SessionStatus
from app.repositories import device_repo, lock_repo, pair_repo, session_repo
from app.services import packet_log
from app.services.crosstest.device_locker import DeviceLocker
from app.services.crosstest.runner import PairRunner, WorkItem


def pick_next_dispatchable(pairs, locked_devices: set[int]):
    """잠기지 않은 첫 번째 페어를 반환한다. 없으면 None."""
    for pair in pairs:
        if pair.src_bacs_id in locked_devices or pair.dst_bacs_id in locked_devices:
            continue
        return pair
    return None


class CrossTestScheduler:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        runner: PairRunner,
        *,
        max_concurrent_pairs: int,
        dispatch_interval_ms: int,
    ) -> None:
        self.session_factory = session_factory
        self.runner = runner
        self.locker = DeviceLocker()
        self.semaphore = asyncio.Semaphore(max_concurrent_pairs)
        self.dispatch_interval = dispatch_interval_ms / 1000.0
        self._queued_sessions: asyncio.Queue[int] = asyncio.Queue()
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    def submit(self, session_id: int) -> None:
        self._queued_sessions.put_nowait(session_id)

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._main_loop())

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            await self._task

    async def _main_loop(self) -> None:
        active: set[asyncio.Task] = set()
        while not self._stop.is_set():
            try:
                sid = await asyncio.wait_for(self._queued_sessions.get(), timeout=0.5)
            except asyncio.TimeoutError:
                # opportunistically prune finished worker tasks
                active = {t for t in active if not t.done()}
                continue
            session_task = asyncio.create_task(self._run_session(sid))
            active.add(session_task)
            session_task.add_done_callback(active.discard)

    async def _run_session(self, session_id: int) -> None:
        logger.info("crosstest.session.start session={}", session_id)
        async with self.session_factory() as db:
            await session_repo.mark_running(db, session_id)
            await db.commit()

        in_flight: set[asyncio.Task] = set()

        while True:
            async with self.session_factory() as db:
                pending = await pair_repo.list_pending_for_session(db, session_id)
            if not pending and not in_flight:
                break

            chosen = pick_next_dispatchable(pending, self.locker.locked_devices())
            if chosen is None:
                if in_flight:
                    done, in_flight = await asyncio.wait(
                        in_flight, return_when=asyncio.FIRST_COMPLETED
                    )
                else:
                    try:
                        await asyncio.wait_for(
                            self.locker.wait_for_release(), timeout=self.dispatch_interval
                        )
                    except asyncio.TimeoutError:
                        pass
                continue

            acquired = await self.locker.try_acquire_pair(
                chosen.src_bacs_id, chosen.dst_bacs_id, session_id=session_id
            )
            if not acquired:
                continue

            async with self.session_factory() as db:
                await lock_repo.add(db, chosen.src_bacs_id, session_id)
                await lock_repo.add(db, chosen.dst_bacs_id, session_id)
                await db.commit()
                devices = await device_repo.get_by_ids(
                    db, [chosen.src_bacs_id, chosen.dst_bacs_id]
                )
            by_id: dict[int, BacsDevice] = {d.id: d for d in devices}
            item = WorkItem(
                pair_id=chosen.id,
                session_id=session_id,
                src_id=chosen.src_bacs_id,
                dst_id=chosen.dst_bacs_id,
            )

            async def _worker_wrapper(it=item, src=by_id[chosen.src_bacs_id],
                                      dst=by_id[chosen.dst_bacs_id]):
                async with self.semaphore:
                    try:
                        await self.runner.run(it, src, dst)
                    finally:
                        await self.locker.release_pair(it.src_id, it.dst_id)

            in_flight.add(asyncio.create_task(_worker_wrapper()))

        async with self.session_factory() as db:
            await session_repo.mark_finished(db, session_id, SessionStatus.completed)
            await db.commit()
        # 패킷 SSE 스트림을 닫도록 sentinel 투입 후 큐 정리
        packet_log.publish_done(session_id)
        # 즉시 삭제 대신 5분 후 해제 — SSE 클라이언트가 늦게 연결해도 히스토리 전달 가능
        packet_log.schedule_cleanup(session_id)
        logger.info("crosstest.session.complete session={}", session_id)
