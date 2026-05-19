from unittest.mock import AsyncMock, MagicMock

import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api import devices as devices_api
from app.api import health as health_api
from app.api import matrix as matrix_api
from app.api import tests as tests_api
from app.db import get_session
from app.models import BacsDevice, PairLatestResult, PairLatestStatus
from app.repositories import user_repo
from app.security import create_access_token, hash_password


@pytest_asyncio.fixture(loop_scope="session")
async def authed_app(engine, db_session):
    user = await user_repo.create(
        db_session, username="bob", password_hash=hash_password("pw")
    )
    db_session.add_all(
        [
            BacsDevice(
                name="b1", node_id=1, ip_address="10.0.0.1", udp_port=5001, tcp_port=6001,
                location=None, enabled=True,
            ),
            BacsDevice(
                name="b2", node_id=2, ip_address="10.0.0.2", udp_port=5001, tcp_port=6001,
                location=None, enabled=True,
            ),
        ]
    )
    await db_session.commit()
    devices = (await db_session.execute(__import__("sqlalchemy").select(BacsDevice))).scalars().all()
    d1, d2 = devices[0], devices[1]

    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _override():
        async with factory() as s:
            yield s

    app = FastAPI()
    app.include_router(devices_api.router)
    app.include_router(health_api.router)
    app.include_router(tests_api.router)
    app.include_router(matrix_api.router)
    app.dependency_overrides[get_session] = _override
    app.state.health_svc = MagicMock(run_once=AsyncMock(return_value=None))
    app.state.crosstest = MagicMock(submit=MagicMock(return_value=None))

    token = create_access_token(subject=user.username)
    yield app, token, (d1.id, d2.id)


async def test_devices_requires_auth(authed_app):
    app, _, _ = authed_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        resp = await ac.get("/devices")
    assert resp.status_code == 401


async def test_list_devices_returns_seeded(authed_app):
    app, token, _ = authed_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        resp = await ac.get("/devices", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    names = sorted(d["name"] for d in resp.json())
    assert names == ["b1", "b2"]


async def test_health_refresh_invokes_service(authed_app):
    app, token, _ = authed_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        resp = await ac.post("/health/refresh", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 202
    app.state.health_svc.run_once.assert_awaited()


async def test_create_test_session_submits_to_scheduler(authed_app):
    app, token, (d1, d2) = authed_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        resp = await ac.post(
            "/tests",
            json={"device_ids": [d1, d2]},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["total_pairs"] == 2
    assert body["status"] == "queued"
    app.state.crosstest.submit.assert_called_once_with(body["id"])


async def test_get_session_404(authed_app):
    app, token, _ = authed_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        resp = await ac.get("/tests/99999", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


async def test_list_pairs_requires_status_filter(authed_app):
    app, token, _ = authed_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        resp = await ac.get("/tests/1/pairs", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400


async def test_matrix_filters_by_device_ids(authed_app, db_session):
    from datetime import datetime

    from app.repositories import session_repo

    app, token, (d1, d2) = authed_app
    user = await user_repo.get_by_username(db_session, "bob")
    ts = await session_repo.create(
        db_session, user_id=user.id, device_ids=[d1, d2], total_pairs=2
    )
    db_session.add(
        PairLatestResult(
            src_bacs_id=d1, dst_bacs_id=d2, status=PairLatestStatus.ok,
            tested_at=datetime.utcnow(), session_id=ts.id, error_message=None,
        )
    )
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        resp = await ac.get(
            f"/pair-matrix?device_ids={d1}&device_ids={d2}",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    cells = resp.json()
    assert len(cells) == 1
    assert cells[0]["src_bacs_id"] == d1
    assert cells[0]["dst_bacs_id"] == d2
    assert cells[0]["status"] == "ok"
