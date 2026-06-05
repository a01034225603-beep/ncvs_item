"""장비 CRUD + 시나리오 목록 API 통합 테스트 (TDD)."""
from unittest.mock import MagicMock

import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api import devices as devices_api
from app.api import tests as tests_api
from app.db import get_session
from app.repositories import user_repo
from app.security import create_access_token, hash_password


@pytest_asyncio.fixture(loop_scope="session")
async def crud_app(engine, db_session):
    user = await user_repo.create(
        db_session, username="crud_user", password_hash=hash_password("pw")
    )
    await db_session.commit()
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _override():
        async with factory() as s:
            yield s

    app = FastAPI()
    app.include_router(devices_api.router)
    app.include_router(tests_api.router)
    app.dependency_overrides[get_session] = _override
    app.state.crosstest = MagicMock(submit=MagicMock(return_value=None))
    token = create_access_token(subject=user.username)
    yield app, token


# ── 장비 CRUD 테스트 ──────────────────────────────────────────────────

async def test_create_device(crud_app):
    """POST /devices -> 201"""
    app, token = crud_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        resp = await ac.post(
            "/devices",
            json={"name": "Dev01", "node_id": 10, "ip_address": "192.168.100.1",
                  "udp_port": 7788, "tcp_port": 7788, "location": "Seoul", "enabled": True},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Dev01"
    assert body["ip_address"] == "192.168.100.1"
    assert body["id"] > 0


async def test_create_device_no_auth(crud_app):
    """인증 없이 POST -> 401"""
    app, _ = crud_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        resp = await ac.post(
            "/devices",
            json={"name": "x", "node_id": 1, "ip_address": "1.1.1.1"},
        )
    assert resp.status_code == 401


async def test_list_devices_includes_created(crud_app):
    """생성 후 목록에 포함"""
    app, token = crud_app
    hdrs = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        cr = await ac.post(
            "/devices",
            json={"name": "ListDev", "node_id": 99, "ip_address": "10.0.99.2"},
            headers=hdrs,
        )
        assert cr.status_code == 201
        did = cr.json()["id"]
        lr = await ac.get("/devices", headers=hdrs)
        assert did in [d["id"] for d in lr.json()]


async def test_update_device(crud_app):
    """수정된 필드만 변경, 나머지 유지"""
    app, token = crud_app
    hdrs = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        cr = await ac.post(
            "/devices",
            json={"name": "OrigDev", "node_id": 20, "ip_address": "10.0.20.2"},
            headers=hdrs,
        )
        did = cr.json()["id"]
        ur = await ac.put(
            f"/devices/{did}",
            json={"name": "UpdatedDev", "location": "Busan"},
            headers=hdrs,
        )
    assert ur.status_code == 200
    body = ur.json()
    assert body["name"] == "UpdatedDev"
    assert body["location"] == "Busan"
    assert body["ip_address"] == "10.0.20.2"


async def test_update_device_not_found(crud_app):
    app, token = crud_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        resp = await ac.put(
            "/devices/99999",
            json={"name": "x"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 404


async def test_delete_device(crud_app):
    """삭제 후 목록에서 제외"""
    app, token = crud_app
    hdrs = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        cr = await ac.post(
            "/devices",
            json={"name": "DelMe", "node_id": 30, "ip_address": "10.0.30.2"},
            headers=hdrs,
        )
        did = cr.json()["id"]
        dr = await ac.delete(f"/devices/{did}", headers=hdrs)
        assert dr.status_code == 204
        lr = await ac.get("/devices", headers=hdrs)
        assert did not in [d["id"] for d in lr.json()]


async def test_delete_device_not_found(crud_app):
    app, token = crud_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        resp = await ac.delete(
            "/devices/99999",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 404


async def test_list_sessions(crud_app):
    """GET /tests -> 200 + 배열"""
    app, token = crud_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        resp = await ac.get("/tests", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
