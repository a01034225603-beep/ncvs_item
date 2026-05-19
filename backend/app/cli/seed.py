"""Run: python -m app.cli.seed admin admin"""
import asyncio
import sys

from sqlalchemy import select

from app.db import SessionLocal
from app.models import BacsDevice
from app.repositories import user_repo
from app.security import hash_password


async def _seed(username: str, password: str) -> None:
    async with SessionLocal() as session:
        if await user_repo.get_by_username(session, username) is None:
            await user_repo.create(
                session, username=username, password_hash=hash_password(password)
            )
        existing = (await session.execute(select(BacsDevice))).scalars().first()
        if existing is None:
            session.add_all(
                BacsDevice(
                    name=f"BACS-{i:03d}",
                    node_id=i % 64,
                    ip_address=f"10.0.0.{i + 1}",
                )
                for i in range(1, 6)
            )
        await session.commit()


if __name__ == "__main__":
    asyncio.run(_seed(sys.argv[1], sys.argv[2]))
