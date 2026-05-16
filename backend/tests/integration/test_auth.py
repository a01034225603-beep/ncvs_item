import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api import auth as auth_api
from app.db import get_session
from app.repositories import user_repo
from app.security import hash_password
from fastapi import FastAPI


@pytest_asyncio.fixture(loop_scope="session")
async def app_with_user(engine, db_session):
    user = await user_repo.create(
        db_session, username="alice", password_hash=hash_password("pw123")
    )
    await db_session.commit()

    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _override_get_session():
        async with factory() as s:
            yield s

    app = FastAPI()
    app.include_router(auth_api.router)
    app.dependency_overrides[get_session] = _override_get_session
    yield app, user


async def test_login_success_returns_token(app_with_user):
    app, _ = app_with_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        resp = await ac.post("/auth/login", json={"username": "alice", "password": "pw123"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


async def test_login_bad_password_returns_401(app_with_user):
    app, _ = app_with_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        resp = await ac.post("/auth/login", json={"username": "alice", "password": "wrong"})
    assert resp.status_code == 401


async def test_login_unknown_user_returns_401(app_with_user):
    app, _ = app_with_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        resp = await ac.post("/auth/login", json={"username": "bob", "password": "pw123"})
    assert resp.status_code == 401
