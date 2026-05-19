from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.cli import seed as seed_mod
from app.models import BacsDevice, User
from app.repositories import user_repo
from app.security import verify_password


async def test_seed_creates_user_and_devices(engine, db_session, monkeypatch):
    factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(seed_mod, "SessionLocal", factory)

    await seed_mod._seed("admin", "adminpw")

    user = await user_repo.get_by_username(db_session, "admin")
    assert user is not None
    assert verify_password("adminpw", user.password_hash)

    devices = (await db_session.execute(select(BacsDevice))).scalars().all()
    assert len(devices) == 5


async def test_seed_is_idempotent(engine, db_session, monkeypatch):
    factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(seed_mod, "SessionLocal", factory)

    await seed_mod._seed("admin", "adminpw")
    await seed_mod._seed("admin", "adminpw")

    users = (await db_session.execute(select(User).where(User.username == "admin"))).scalars().all()
    assert len(users) == 1
    devices = (await db_session.execute(select(BacsDevice))).scalars().all()
    assert len(devices) == 5
