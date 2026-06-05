from contextlib import asynccontextmanager
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api import auth as auth_api
from app.api import devices as devices_api
from app.api import health as health_api
from app.api import matrix as matrix_api
from app.api import scenarios as scenarios_api
from app.api import tests as tests_api
from app.config import settings
from app.db import SessionLocal
from app.models import SessionStatus
from app.protocol.crosstest_proto import BacsTcpCrossTestProtocol
from app.repositories import lock_repo, session_repo
from app.services.crosstest.runner import PairRunner
from app.services.crosstest.scheduler import CrossTestScheduler
from app.services.health_service import HealthCheckService


async def _periodic_health(svc: HealthCheckService) -> None:
    async with SessionLocal() as db:
        await svc.run_once(db)


async def _recover_state() -> None:
    async with SessionLocal() as db:
        await lock_repo.clear_all(db)
        active = await session_repo.list_active(db)
        for s in active:
            await session_repo.mark_finished(db, s.id, SessionStatus.failed)
        await db.commit()
        logger.info("startup.recovery cleared_sessions={}", len(active))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _recover_state()

    # ── 헬스체크 서비스 ────────────────────────────────────────────
    health_svc = HealthCheckService(
        timeout=settings.HEALTH_CHECK_TIMEOUT_SEC,
        concurrency=settings.HEALTH_CHECK_CONCURRENCY,
    )
    app.state.health_svc = health_svc

    # ── TCP 호출시험 스케줄러 ──────────────────────────────────────
    proto = BacsTcpCrossTestProtocol()
    runner = PairRunner(
        proto=proto,
        session_factory=SessionLocal,
        pair_timeout=settings.CROSSTEST_PAIR_TIMEOUT_SEC,
    )
    scheduler = CrossTestScheduler(
        session_factory=SessionLocal,
        runner=runner,
        max_concurrent_pairs=settings.CROSSTEST_MAX_CONCURRENT_PAIRS,
        dispatch_interval_ms=settings.CROSSTEST_DISPATCH_INTERVAL_MS,
    )
    scheduler.start()
    app.state.crosstest_scheduler = scheduler

    # ── APScheduler (헬스체크 주기 잡) ────────────────────────────
    aps = AsyncIOScheduler()
    aps.add_job(
        _periodic_health,
        IntervalTrigger(seconds=settings.HEALTH_CHECK_INTERVAL_SEC),
        args=[health_svc],
        next_run_time=datetime.now(),  # 시작 직후 즉시 1회 실행, 이후 주기적으로 실행
    )
    aps.start()
    app.state.aps = aps
    logger.info("startup.complete")

    yield

    await scheduler.stop()
    aps.shutdown(wait=False)
    logger.info("shutdown.complete")


app = FastAPI(title="NCVS BACS Monitor", lifespan=lifespan)

# 브라우저 → 백엔드 직접 SSE 연결을 위한 CORS 허용
# EventSource는 쿼리스트링 토큰 인증을 사용하므로 credentials 불필요
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(auth_api.router)
app.include_router(devices_api.router)
app.include_router(health_api.router)
app.include_router(scenarios_api.router)
app.include_router(tests_api.router)
app.include_router(matrix_api.router)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
