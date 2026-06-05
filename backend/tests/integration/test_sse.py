"""
SSE 엔드포인트 통합 테스트 — GET /tests/{session_id}/stream
스킬 2 (TDD): 테스트 먼저 작성 -> 실패 확인 -> 구현 -> 통과 확인
"""
import json
from unittest.mock import MagicMock, patch

import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api import tests as tests_api
from app.db import get_session
from app.models import SessionStatus
from app.repositories import session_repo, user_repo
from app.security import create_access_token, hash_password


@pytest_asyncio.fixture(loop_scope="session")
async def sse_app(engine, db_session):
    user = await user_repo.create(
        db_session, username="sse_tester", password_hash=hash_password("pw")
    )
    await db_session.commit()
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _override():
        async with factory() as s:
            yield s

    app = FastAPI()
    app.include_router(tests_api.router)
    app.dependency_overrides[get_session] = _override
    app.state.crosstest = MagicMock(submit=MagicMock(return_value=None))
    token = create_access_token(subject=user.username)
    yield app, token, factory, user.id


async def test_sse_stream_content_type(sse_app):
    """SSE 엔드포인트가 text/event-stream Content-Type을 반환해야 한다"""
    app, token, factory, uid = sse_app
    async with factory() as db:
        s = await session_repo.create(db, user_id=uid, device_ids=[1, 2], total_pairs=2)
        await session_repo.mark_finished(db, s.id, SessionStatus.completed)
        await db.commit()
        sid = s.id
    with patch("app.api.tests.SessionLocal", factory):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            async with ac.stream("GET", f"/tests/{sid}/stream?token={token}") as resp:
                assert resp.status_code == 200
                assert "text/event-stream" in resp.headers["content-type"]


async def test_sse_stream_emits_valid_session_json(sse_app):
    """SSE 스트림이 유효한 JSON 세션 데이터(id, status, total_pairs 포함)를 방출해야 한다"""
    app, token, factory, uid = sse_app
    async with factory() as db:
        s = await session_repo.create(db, user_id=uid, device_ids=[1, 2], total_pairs=2)
        await session_repo.mark_finished(db, s.id, SessionStatus.completed)
        await db.commit()
        sid = s.id
    events = []
    with patch("app.api.tests.SessionLocal", factory):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            async with ac.stream("GET", f"/tests/{sid}/stream?token={token}") as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data:"):
                        raw = line[5:].strip()
                        if raw:
                            events.append(json.loads(raw))
    assert len(events) >= 1
    first = events[0]
    assert first["id"] == sid
    assert "status" in first
    assert "total_pairs" in first


async def test_sse_stream_404_for_unknown_session(sse_app):
    """존재하지 않는 세션 ID 요청 시 HTTP 404를 반환해야 한다"""
    app, token, factory, _ = sse_app
    with patch("app.api.tests.SessionLocal", factory):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            async with ac.stream("GET", f"/tests/99999/stream?token={token}") as resp:
                assert resp.status_code == 404


async def test_sse_stream_422_without_token(sse_app):
    """token 쿼리 파라미터 없이 요청 시 422를 반환해야 한다"""
    app, _, factory, uid = sse_app
    async with factory() as db:
        s = await session_repo.create(db, user_id=uid, device_ids=[1, 2], total_pairs=2)
        await db.commit()
        sid = s.id
    with patch("app.api.tests.SessionLocal", factory):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            async with ac.stream("GET", f"/tests/{sid}/stream") as resp:
                assert resp.status_code == 422


async def test_sse_stream_401_with_invalid_token(sse_app):
    """유효하지 않은 토큰으로 요청 시 401을 반환해야 한다"""
    app, _, factory, uid = sse_app
    async with factory() as db:
        s = await session_repo.create(db, user_id=uid, device_ids=[1, 2], total_pairs=2)
        await db.commit()
        sid = s.id
    with patch("app.api.tests.SessionLocal", factory):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            async with ac.stream("GET", f"/tests/{sid}/stream?token=invalid.token.here") as resp:
                assert resp.status_code == 401


async def test_sse_stream_closes_on_terminal_status(sse_app):
    """세션이 terminal 상태(completed)이면 done 이벤트 후 스트림이 종료되어야 한다"""
    app, token, factory, uid = sse_app
    async with factory() as db:
        s = await session_repo.create(db, user_id=uid, device_ids=[1, 2], total_pairs=2)
        await session_repo.mark_finished(db, s.id, SessionStatus.completed)
        await db.commit()
        sid = s.id
    lines = []
    with patch("app.api.tests.SessionLocal", factory):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            async with ac.stream("GET", f"/tests/{sid}/stream?token={token}") as resp:
                async for line in resp.aiter_lines():
                    lines.append(line)
    assert any("done" in line for line in lines)
