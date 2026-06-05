import asyncio

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import BacsDevice, SessionStatus
from app.repositories import device_repo, lock_repo, pair_repo, session_repo
from app.services import packet_log
from app.services.crosstest.device_locker import DeviceLocker
from app.services.crosstest.runner import PairRunner, WorkItem


def pick_all_dispatchable(pairs, locked_devices: set[int]) -> list:
    """
    현재 실행 가능한 페어 전체를 한 번에 반환한다 (배치 dispatch).

    알고리즘:
      - 이미 잠긴 장비(locked_devices)는 건너뜀
      - 이번 배치 안에서도 장비 중복 사용 금지
        (발신·수신 역할 무관하게 장비 하나는 배치당 1번만 등장)
      - 이 규칙은 프론트엔드 rounds.ts 의 computeRounds() 와 동일한 제약

    returns: 이번 루프에서 동시에 dispatch 할 수 있는 페어 목록.
             빈 리스트이면 현재 dispatch 불가 (in_flight 완료 대기 필요).
    """
    batch_used: set[int] = set()  # 이번 배치에서 이미 선택된 장비
    result = []
    for pair in pairs:
        src, dst = pair.src_bacs_id, pair.dst_bacs_id
        # 이미 잠긴 장비 또는 이번 배치에서 사용 예정인 장비이면 건너뜀
        if src in locked_devices or dst in locked_devices:
            continue
        if src in batch_used or dst in batch_used:
            continue
        batch_used.add(src)
        batch_used.add(dst)
        result.append(pair)
    return result


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
            # ── 취소 여부 먼저 확인 ──────────────────────────────────────
            async with self.session_factory() as db:
                current_session = await session_repo.get(db, session_id)
            if current_session is None or current_session.status == SessionStatus.cancelled:
                # 실행 중인 태스크가 있으면 완료를 기다린 후 중단
                # (이미 TCP 연결된 페어는 강제 종료하지 않고 자연 완료 대기)
                if in_flight:
                    await asyncio.wait(in_flight, return_when=asyncio.ALL_COMPLETED)
                # 남은 pending 페어 전부 skipped 처리
                async with self.session_factory() as db:
                    await pair_repo.mark_pending_as_skipped(db, session_id)
                    await db.commit()
                logger.info("crosstest.session.cancelled session={}", session_id)
                # SSE 스트림 종료 알림 후 반환 (completed 덮어쓰기 없음)
                packet_log.publish_done(session_id)
                packet_log.schedule_cleanup(session_id)
                return

            async with self.session_factory() as db:
                pending = await pair_repo.list_pending_for_session(db, session_id)
            if not pending and not in_flight:
                break

            # 현재 잠긴 장비 집합을 기준으로 이번 배치 전체를 한 번에 선택
            batch = pick_all_dispatchable(pending, self.locker.locked_devices())

            if not batch:
                # 배치가 비어있음 = 모든 남은 페어가 in_flight 완료를 기다려야 함
                if in_flight:
                    # 가장 먼저 끝나는 태스크 완료를 기다린 후 재시도
                    done, in_flight = await asyncio.wait(
                        in_flight, return_when=asyncio.FIRST_COMPLETED
                    )
                else:
                    # in_flight 도 없는데 배치도 없다면 release 이벤트 대기
                    try:
                        await asyncio.wait_for(
                            self.locker.wait_for_release(), timeout=self.dispatch_interval
                        )
                    except asyncio.TimeoutError:
                        pass
                continue

            # 배치 내 페어 전체 잠금 시도 → 잠금 성공한 것만 dispatch
            for chosen in batch:
                acquired = await self.locker.try_acquire_pair(
                    chosen.src_bacs_id, chosen.dst_bacs_id, session_id=session_id
                )
                if not acquired:
                    # 극히 드문 경합(다른 세션과 장비 공유) 시 건너뜀
                    # 다음 배치 루프에서 자연스럽게 재시도됨
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

        # 루프 정상 종료 = 모든 페어 완료
        # cancelled 상태는 위 루프 안에서 이미 처리되고 return 됐으므로
        # 여기까지 도달하면 반드시 completed 로 전환해도 안전
        async with self.session_factory() as db:
            await session_repo.mark_finished(db, session_id, SessionStatus.completed)
            await db.commit()
        # 패킷 SSE 스트림을 닫도록 sentinel 투입 후 큐 정리
        packet_log.publish_done(session_id)
        # 즉시 삭제 대신 5분 후 해제 — SSE 클라이언트가 늦게 연결해도 히스토리 전달 가능
        packet_log.schedule_cleanup(session_id)
        logger.info("crosstest.session.complete session={}", session_id)
