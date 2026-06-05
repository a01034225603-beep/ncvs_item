from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


# aiomysql 버전 호환 이슈: ping(reconnect) 시그니처 불일치 → pool_pre_ping 비활성화
engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=False, pool_size=10)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
