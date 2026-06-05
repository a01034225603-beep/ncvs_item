import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from jwt import InvalidTokenError
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal, get_session
from app.deps import get_current_user
from app.models import SessionStatus, User
from app.repositories import pair_repo, scenario_repo, session_repo, user_repo
from app.schemas.pair import PairOut
from app.schemas.session import SessionOut, SessionWithPairsOut
from app.security import decode_access_token
from app.services import packet_log
from app.services.session_service import cancel_session, create_session_from_scenario


class TestCreateBody(BaseModel):
    scenario_id: int

# SSE 스트림 종료 대상 상태 집합
_TERMINAL = {SessionStatus.completed, SessionStatus.cancelled, SessionStatus.failed}

router = APIRouter(prefix="/tests", tags=["tests"])


@router.get("", response_model=list[SessionOut])
async def list_sessions(
    scenario_id: int | None = None,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """시나리오(테스트 세션) 전체 목록 조회. scenario_id 지정 시 해당 시나리오 세션만 반환."""
    if scenario_id is not None:
        return await session_repo.list_by_scenario(session, scenario_id)
    return await session_repo.list_all(session)


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def create(
    body: TestCreateBody,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """시나리오 ID를 받아 호출시험 세션을 생성하고 스케줄러에 제출한다."""
    # 시나리오 조회
    scenario = await scenario_repo.get(session, body.scenario_id)
    if scenario is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "scenario not found")

    # 발신 + 착신 장비 ID 목록 합산 (중복 허용 — 양방향 페어 생성)
    all_device_ids = list(scenario.sender_device_ids) + list(scenario.receiver_device_ids)
    if len(set(all_device_ids)) < 2:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "시나리오에 장비가 2대 이상 필요합니다.")

    test_session = await create_session_from_scenario(
        session,
        user_id=current_user.id,
        scenario_id=scenario.id,
        sender_device_ids=scenario.sender_device_ids,
        receiver_device_ids=scenario.receiver_device_ids,
    )

    # 스케줄러에 세션 제출 (app.state에 등록된 스케줄러 사용)
    scheduler = getattr(request.app.state, "crosstest_scheduler", None)
    if scheduler is not None:
        scheduler.submit(test_session.id)

    return test_session


@router.get("/{session_id}", response_model=SessionOut)
async def get_one(
    session_id: int,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    ts = await session_repo.get(session, session_id)
    if ts is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "session not found")
    return ts


@router.get("/{session_id}/pairs", response_model=list[PairOut])
async def list_pairs(
    session_id: int,
    status_filter: str | None = None,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if status_filter == "running":
        return await pair_repo.list_running(session, session_id)
    if status_filter == "pending":
        return await pair_repo.list_pending_for_session(session, session_id)
    raise HTTPException(status.HTTP_400_BAD_REQUEST, "use status_filter=running|pending")


@router.post("/{session_id}/cancel", status_code=status.HTTP_202_ACCEPTED)
async def cancel(
    session_id: int,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await cancel_session(session, session_id)
    return {"status": "cancelled"}


@router.get("/{session_id}/stream")
async def stream_session(
    session_id: int,
    token: str = Query(..., description="JWT 토큰 (EventSource는 헤더 미지원으로 쿼리 전달)"),
):
    """세션 상태를 SSE(Server-Sent Events)로 실시간 스트리밍한다.

    EventSource는 커스텀 헤더를 지원하지 않으므로 token을 쿼리 파라미터로 받는다.
    세션이 terminal 상태(completed/cancelled/failed)가 되면 자동 종료된다.
    """
    # ── 1. 토큰 검증 ──────────────────────────────────────────────
    try:
        payload = decode_access_token(token)
        username = payload.get("sub")
        if not username:
            raise InvalidTokenError("sub missing")
    except InvalidTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token") from exc

    # ── 2. 유저 존재 확인 ──────────────────────────────────────────
    async with SessionLocal() as db:
        user = await user_repo.get_by_username(db, username)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user not found")

    # ── 3. 세션 존재 확인 (스트림 시작 전 404 처리) ────────────────
    async with SessionLocal() as db:
        ts = await session_repo.get(db, session_id)
    if ts is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "session not found")

    # ── 4. SSE 이벤트 제너레이터 ──────────────────────────────────
    async def event_gen():
        while True:
            async with SessionLocal() as db:
                ts = await session_repo.get(db, session_id)

            if ts is None:
                # 세션이 사라진 경우 에러 이벤트 후 종료
                yield "event: error\ndata: {\"detail\": \"session not found\"}\n\n"
                return

            # 현재 상태 + 전체 페어 상태를 JSON으로 직렬화하여 방출
            async with SessionLocal() as db:
                pair_rows = await pair_repo.list_all_for_session(db, session_id)
            data = SessionWithPairsOut(
                **SessionOut.model_validate(ts).model_dump(),
                pairs=pair_rows,
            ).model_dump_json()
            yield f"data: {data}\n\n"

            # terminal 상태면 done 이벤트 후 스트림 종료
            if ts.status in _TERMINAL:
                yield "event: done\ndata: {}\n\n"
                return

            # 1초 대기 후 다음 폴링
            await asyncio.sleep(1)

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # nginx 버퍼링 비활성화
            "Connection": "keep-alive",
        },
    )


@router.get("/{session_id}/packets")
async def stream_packets(
    session_id: int,
    token: str = Query(..., description="JWT 토큰"),
):
    """패킷 이벤트를 SSE 로 실시간 스트리밍한다.

    호출시험 진행 중 각 TCP 패킷(TX/RX)이 발생할 때마다 이벤트를 방출한다.
    세션이 종료되면 'done' 이벤트 후 스트림을 닫는다.

    각 data 이벤트의 JSON 필드:
        session_id  : int
        pair_label  : str  (예: "192.168.1.10 → 192.168.1.10")
        direction   : "TX" | "RX"
        step        : str  (예: "CONNECT_REQ", "STARTUP_RPT", "CALL_REQ[Port=0]")
        hex_dump    : str  (예: "01 10 09 00 ...")
        parsed      : dict (BACS_Control.md §1.3 기준 파싱 결과)
        ts          : str  (ISO 8601 UTC)
    """
    # ── 1. 토큰 검증 ──────────────────────────────────────────────
    try:
        payload = decode_access_token(token)
        username = payload.get("sub")
        if not username:
            raise InvalidTokenError("sub missing")
    except InvalidTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token") from exc

    async with SessionLocal() as db:
        user = await user_repo.get_by_username(db, username)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user not found")

    async with SessionLocal() as db:
        ts = await session_repo.get(db, session_id)
    if ts is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "session not found")

    # ── 2. SSE 제너레이터 ─────────────────────────────────────────
    async def event_gen():
        # ① 히스토리 먼저 재생 — 늦게 연결된 클라이언트도 전체 이력을 받게 됨
        history = packet_log.get_history(session_id)
        for ev in history:
            data = json.dumps(ev.to_json_dict(), ensure_ascii=False)
            yield f"data: {data}\n\n"

        # ② 세션이 이미 완료된 상태면 done 방출 후 즉시 종료
        if packet_log.is_done(session_id):
            yield "event: done\ndata: {}\n\n"
            return

        # ③ 실시간 큐에서 추가 이벤트 스트리밍
        q = await packet_log.subscribe(session_id)
        # 이미 큐에 쌓인 이벤트를 빠르게 드레인 (히스토리 이후 발생분)
        history_ts_set = {ev.ts for ev in history}
        while True:
            try:
                # 0.5초 timeout 으로 큐에서 이벤트를 꺼냄
                event = await asyncio.wait_for(q.get(), timeout=0.5)
            except asyncio.TimeoutError:
                # 세션이 이미 종료됐으면 done 방출 후 종료
                async with SessionLocal() as db:
                    current = await session_repo.get(db, session_id)
                if current is not None and current.status in _TERMINAL:
                    yield "event: done\ndata: {}\n\n"
                    return
                # keepalive (SSE 연결 유지)
                yield ": keepalive\n\n"
                continue

            if event is None:
                # sentinel — 세션 종료
                yield "event: done\ndata: {}\n\n"
                return

            # 이미 히스토리로 보낸 이벤트는 중복 방송 방지
            if event.ts in history_ts_set:
                continue

            data = json.dumps(event.to_json_dict(), ensure_ascii=False)
            yield f"data: {data}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
