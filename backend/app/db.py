"""
DB 연결 설정 모듈.

역할:
  - MySQL 비동기 엔진(aiomysql 드라이버)을 초기화한다.
  - SessionLocal: 코드 전체에서 DB 세션을 만들 때 사용하는 팩토리.
  - get_session():  FastAPI 라우터에서 Depends()로 주입받는 세션 제너레이터.
  - Base:           모든 ORM 모델이 상속하는 기반 클래스.
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    """모든 SQLAlchemy ORM 모델의 공통 기반 클래스."""
    pass


# aiomysql 버전 호환 이슈: ping(reconnect) 시그니처 불일치 → pool_pre_ping 비활성화
# pool_size=10: 동시에 열어둘 수 있는 DB 연결 최대 수
engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=False, pool_size=10)

# expire_on_commit=False: commit 후 ORM 객체를 자동 만료하지 않음
# (만료되면 다음 접근 시 추가 쿼리 발생 → 비동기 환경에서 문제 발생 가능)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncSession:
    """FastAPI Depends()용 DB 세션 제너레이터. 요청 하나당 세션 하나를 생성한다."""
    async with SessionLocal() as session:
        yield session
