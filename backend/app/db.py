from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

# SQLite: check_same_thread=False 필요 (asyncio 환경에서 스레드 공유)
# MySQL: pool_pre_ping 비활성화 (aiomysql ping 시그니처 불일치 이슈)
_connect_args = {"check_same_thread": False} if _is_sqlite else {}
_engine_kwargs = {"connect_args": _connect_args} if _is_sqlite else {"pool_pre_ping": False, "pool_size": 10}

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
