# BACS Monitoring & Cross-Test System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a BACS monitoring system with periodic UDP health-check and a cross-test scheduler that verifies send/receive between selected BACS devices under device-level concurrency locks.

**Architecture:** Single FastAPI process (asyncio) running APScheduler for periodic health-checks and an in-process cross-test scheduler with per-device asyncio locks; MySQL stores devices, latest health, sessions, pairs, and pair-latest results; Next.js polls REST endpoints every ~3s.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x async, MySQL 8, Alembic, APScheduler, asyncio, pytest + pytest-asyncio, bcrypt, PyJWT, Next.js 14 (App Router), TypeScript, docker-compose.

**Spec reference:** `docs/superpowers/specs/2026-05-15-bacs-monitoring-design.md`

---

## File Structure

### Backend (`backend/`)

```
backend/
├─ pyproject.toml                 # uv + pytest + ruff config
├─ alembic.ini
├─ alembic/
│  ├─ env.py
│  └─ versions/                   # migrations
├─ app/
│  ├─ __init__.py
│  ├─ main.py                     # FastAPI app, lifespan
│  ├─ config.py                   # pydantic-settings (.env)
│  ├─ db.py                       # async engine, session factory
│  ├─ deps.py                     # FastAPI dependencies (db, current_user)
│  ├─ security.py                 # bcrypt, JWT encode/decode
│  ├─ logging_setup.py
│  ├─ models/
│  │  ├─ __init__.py
│  │  ├─ user.py
│  │  ├─ bacs.py                  # BacsDevice
│  │  ├─ health.py                # DeviceHealth
│  │  ├─ session.py               # TestSession
│  │  ├─ pair.py                  # TestSessionPair, PairLatestResult
│  │  └─ lock.py                  # DeviceLock
│  ├─ schemas/                    # Pydantic DTOs
│  │  ├─ auth.py
│  │  ├─ device.py
│  │  ├─ health.py
│  │  ├─ session.py
│  │  └─ pair.py
│  ├─ repositories/               # async SQLAlchemy queries
│  │  ├─ user_repo.py
│  │  ├─ device_repo.py
│  │  ├─ health_repo.py
│  │  ├─ session_repo.py
│  │  ├─ pair_repo.py
│  │  └─ lock_repo.py
│  ├─ api/
│  │  ├─ auth.py
│  │  ├─ devices.py
│  │  ├─ health.py
│  │  ├─ tests.py
│  │  └─ matrix.py
│  ├─ services/
│  │  ├─ health_service.py
│  │  ├─ session_service.py
│  │  └─ crosstest/
│  │     ├─ scheduler.py
│  │     ├─ device_locker.py
│  │     └─ runner.py
│  └─ protocol/
│     ├─ constants.py             # Type/MsgType constants
│     ├─ messages.py              # pack/unpack helpers
│     ├─ udp_client.py            # Heartbeat
│     ├─ tcp_client.py            # TCP control (skeleton)
│     └─ crosstest_proto.py       # Stub impl behind interface (TBD)
└─ tests/
   ├─ conftest.py                 # DB fixtures, simulator fixture
   ├─ unit/
   │  ├─ test_messages.py
   │  ├─ test_device_locker.py
   │  ├─ test_scheduler_pick.py
   │  └─ test_security.py
   ├─ integration/
   │  ├─ test_health_flow.py
   │  ├─ test_crosstest_flow.py
   │  └─ test_concurrent_sessions.py
   └─ simulator/
      └─ fake_bacs.py             # asyncio UDP/TCP echo server
```

### Frontend (`frontend/`)

```
frontend/
├─ package.json
├─ next.config.mjs
├─ tsconfig.json
├─ src/
│  ├─ app/
│  │  ├─ layout.tsx
│  │  ├─ login/page.tsx
│  │  ├─ devices/page.tsx          # main dashboard
│  │  ├─ tests/[id]/page.tsx       # progress page
│  │  └─ matrix/page.tsx
│  ├─ lib/
│  │  ├─ api.ts                    # fetch wrappers
│  │  └─ types.ts
│  └─ components/
│     ├─ DeviceTable.tsx
│     ├─ HealthBadge.tsx
│     ├─ TestProgress.tsx
│     └─ Matrix.tsx
```

### Root

```
docker-compose.yml
.env.example
README.md
```

---

## Phase 0: Bootstrap

### Task 0: Repository scaffold

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/tests/__init__.py`
- Create: `.env.example`
- Create: `docker-compose.yml`
- Create: `.gitignore`

- [ ] **Step 1: Create `backend/pyproject.toml`**

```toml
[project]
name = "ncvs-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.110",
  "uvicorn[standard]>=0.27",
  "sqlalchemy[asyncio]>=2.0",
  "aiomysql>=0.2",
  "alembic>=1.13",
  "pydantic>=2.6",
  "pydantic-settings>=2.2",
  "apscheduler>=3.10",
  "passlib[bcrypt]>=1.7",
  "pyjwt>=2.8",
  "loguru>=0.7",
]

[project.optional-dependencies]
dev = [
  "pytest>=8",
  "pytest-asyncio>=0.23",
  "httpx>=0.27",
  "ruff>=0.4",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py312"
```

- [ ] **Step 2: Create `.env.example`**

```dotenv
DATABASE_URL=mysql+aiomysql://ncvs:ncvs@localhost:3306/ncvs
JWT_SECRET=change-me-in-prod
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

HEALTH_CHECK_INTERVAL_SEC=60
HEALTH_CHECK_TIMEOUT_SEC=3
HEALTH_CHECK_CONCURRENCY=50

CROSSTEST_PAIR_TIMEOUT_SEC=70
CROSSTEST_MAX_CONCURRENT_PAIRS=150
CROSSTEST_DISPATCH_INTERVAL_MS=100
```

- [ ] **Step 3: Create `docker-compose.yml`**

```yaml
services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: root
      MYSQL_DATABASE: ncvs
      MYSQL_USER: ncvs
      MYSQL_PASSWORD: ncvs
    ports: ["3306:3306"]
    volumes: ["mysql-data:/var/lib/mysql"]
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 5s
      retries: 10

  backend:
    build: ./backend
    env_file: .env
    ports: ["8000:8000"]
    depends_on:
      mysql: { condition: service_healthy }

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [backend]

volumes:
  mysql-data:
```

- [ ] **Step 4: Create `.gitignore`**

```
__pycache__/
*.pyc
.venv/
node_modules/
.next/
.env
```

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml backend/app/__init__.py backend/tests/__init__.py \
        .env.example docker-compose.yml .gitignore
git commit -m "chore: scaffold backend and compose"
```

---

### Task 1: Settings + DB engine

**Files:**
- Create: `backend/app/config.py`
- Create: `backend/app/db.py`

- [ ] **Step 1: Create `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    HEALTH_CHECK_INTERVAL_SEC: int = 60
    HEALTH_CHECK_TIMEOUT_SEC: int = 3
    HEALTH_CHECK_CONCURRENCY: int = 50

    CROSSTEST_PAIR_TIMEOUT_SEC: int = 70
    CROSSTEST_MAX_CONCURRENT_PAIRS: int = 150
    CROSSTEST_DISPATCH_INTERVAL_MS: int = 100


settings = Settings()
```

- [ ] **Step 2: Create `backend/app/db.py`**

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True, pool_size=10)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/config.py backend/app/db.py
git commit -m "feat(backend): add settings and async DB engine"
```

---

## Phase 1: Data model & migrations

### Task 2: ORM models

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/bacs.py`
- Create: `backend/app/models/health.py`
- Create: `backend/app/models/session.py`
- Create: `backend/app/models/pair.py`
- Create: `backend/app/models/lock.py`

- [ ] **Step 1: Create `backend/app/models/user.py`**

```python
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 2: Create `backend/app/models/bacs.py`**

```python
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class BacsDevice(Base):
    __tablename__ = "bacs_devices"
    __table_args__ = (UniqueConstraint("ip_address", "udp_port", name="uq_bacs_ip_port"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    node_id: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    udp_port: Mapped[int] = mapped_column(Integer, default=7788)
    tcp_port: Mapped[int] = mapped_column(Integer, default=7788)
    location: Mapped[str | None] = mapped_column(String(255))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
```

- [ ] **Step 3: Create `backend/app/models/health.py`**

```python
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class HealthStatus(str, PyEnum):
    ok = "ok"
    fail = "fail"
    unknown = "unknown"


class DeviceHealth(Base):
    __tablename__ = "device_health"

    bacs_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("bacs_devices.id", ondelete="CASCADE"), primary_key=True
    )
    status: Mapped[HealthStatus] = mapped_column(Enum(HealthStatus), default=HealthStatus.unknown)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_ok_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_error: Mapped[str | None] = mapped_column(String(255))
    consecutive_fail: Mapped[int] = mapped_column(Integer, default=0)
```

- [ ] **Step 4: Create `backend/app/models/session.py`**

```python
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import JSON, BigInteger, DateTime, Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class SessionStatus(str, PyEnum):
    queued = "queued"
    running = "running"
    completed = "completed"
    cancelled = "cancelled"
    failed = "failed"


class TestSession(Base):
    __tablename__ = "test_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    status: Mapped[SessionStatus] = mapped_column(Enum(SessionStatus), default=SessionStatus.queued)
    device_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    total_pairs: Mapped[int] = mapped_column(Integer, default=0)
    done_pairs: Mapped[int] = mapped_column(Integer, default=0)
    ok_pairs: Mapped[int] = mapped_column(Integer, default=0)
    fail_pairs: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
```

- [ ] **Step 5: Create `backend/app/models/pair.py`**

```python
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class PairStatus(str, PyEnum):
    pending = "pending"
    running = "running"
    ok = "ok"
    fail = "fail"
    skipped = "skipped"


class PairLatestStatus(str, PyEnum):
    ok = "ok"
    fail = "fail"


class TestSessionPair(Base):
    __tablename__ = "test_session_pairs"
    __table_args__ = (
        Index("ix_session_status", "session_id", "status"),
        Index("ix_pair_src", "src_bacs_id"),
        Index("ix_pair_dst", "dst_bacs_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("test_sessions.id"))
    src_bacs_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("bacs_devices.id"))
    dst_bacs_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("bacs_devices.id"))
    status: Mapped[PairStatus] = mapped_column(Enum(PairStatus), default=PairStatus.pending)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    error_message: Mapped[str | None] = mapped_column(String(255))


class PairLatestResult(Base):
    __tablename__ = "pair_latest_result"

    src_bacs_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("bacs_devices.id"), primary_key=True
    )
    dst_bacs_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("bacs_devices.id"), primary_key=True
    )
    status: Mapped[PairLatestStatus] = mapped_column(Enum(PairLatestStatus), nullable=False)
    tested_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    session_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("test_sessions.id"))
    error_message: Mapped[str | None] = mapped_column(String(255))
```

- [ ] **Step 6: Create `backend/app/models/lock.py`**

```python
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class DeviceLock(Base):
    __tablename__ = "device_locks"

    bacs_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("bacs_devices.id"), primary_key=True
    )
    session_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("test_sessions.id"))
    acquired_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 7: Create `backend/app/models/__init__.py`**

```python
from app.models.bacs import BacsDevice
from app.models.health import DeviceHealth, HealthStatus
from app.models.lock import DeviceLock
from app.models.pair import (
    PairLatestResult,
    PairLatestStatus,
    PairStatus,
    TestSessionPair,
)
from app.models.session import SessionStatus, TestSession
from app.models.user import User

__all__ = [
    "User",
    "BacsDevice",
    "DeviceHealth",
    "HealthStatus",
    "TestSession",
    "SessionStatus",
    "TestSessionPair",
    "PairStatus",
    "PairLatestResult",
    "PairLatestStatus",
    "DeviceLock",
]
```

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/
git commit -m "feat(models): add ORM models for users, bacs, health, sessions, pairs, locks"
```

---

### Task 3: Alembic init + first migration

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/0001_initial.py`

- [ ] **Step 1: Initialize Alembic config (`backend/alembic.ini`)**

```ini
[alembic]
script_location = alembic
sqlalchemy.url = mysql+pymysql://ncvs:ncvs@localhost:3306/ncvs

[loggers]
keys = root,sqlalchemy,alembic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handlers]
keys = console

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatters]
keys = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
```

- [ ] **Step 2: Create `backend/alembic/env.py`**

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import settings
from app.db import Base
from app.models import *  # noqa: F401,F403

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
sync_url = settings.DATABASE_URL.replace("+aiomysql", "+pymysql")
config.set_main_option("sqlalchemy.url", sync_url)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(url=sync_url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 3: Create `backend/alembic/script.py.mako`** (standard Alembic template)

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 4: Start MySQL via compose and autogenerate migration**

```bash
docker compose up -d mysql
cd backend && alembic revision --autogenerate -m "initial schema"
```

Expected: a new file `backend/alembic/versions/<hash>_initial_schema.py` containing all tables. Rename file to `0001_initial.py` and revision id to `0001`.

- [ ] **Step 5: Apply migration**

```bash
cd backend && alembic upgrade head
```

Expected: tables created. Verify with `docker exec -it $(docker compose ps -q mysql) mysql -uncvs -pncvs ncvs -e 'show tables'` — should list all 7 tables.

- [ ] **Step 6: Commit**

```bash
git add backend/alembic.ini backend/alembic/env.py backend/alembic/script.py.mako \
        backend/alembic/versions/
git commit -m "feat(migrations): initial schema"
```

---

## Phase 2: Protocol layer (TDD)

### Task 4: UDP Heartbeat message pack/unpack

**Files:**
- Create: `backend/app/protocol/__init__.py`
- Create: `backend/app/protocol/constants.py`
- Create: `backend/app/protocol/messages.py`
- Test: `backend/tests/unit/test_messages.py`

- [ ] **Step 1: Write the failing test (`backend/tests/unit/test_messages.py`)**

Test bytes derived from `BACS_Control.md` §1.2.1 (`SE_MA_Connect_REQ`: `01 10 05 00 00 00 12 00 00` ; `MA_SE_Connect_RPT` with alive=0xFF: `01 01 0D 00 00 00 92 08 00 FF 00 00 00 00 00 00 00`).

```python
import pytest

from app.protocol.messages import (
    ConnectReply,
    build_connect_request,
    parse_connect_reply,
)


def test_build_connect_request_matches_spec():
    expected = bytes([0x01, 0x10, 0x05, 0x00, 0x00, 0x00, 0x12, 0x00, 0x00])
    assert build_connect_request(node_id=0) == expected


def test_parse_connect_reply_returns_alive_bitmap():
    raw = bytes(
        [0x01, 0x01, 0x0D, 0x00, 0x00, 0x00, 0x92, 0x08, 0x00,
         0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
    )
    reply = parse_connect_reply(raw)
    assert isinstance(reply, ConnectReply)
    assert reply.source_id == 0
    assert reply.alive == 0xFF


def test_parse_rejects_wrong_type():
    bad = bytes([0xFF, 0xFF, 0x0D, 0x00]) + b"\x00" * 13
    with pytest.raises(ValueError):
        parse_connect_reply(bad)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/unit/test_messages.py -v
```

Expected: ImportError or AttributeError (module/symbols not defined).

- [ ] **Step 3: Create `backend/app/protocol/constants.py`**

```python
TCP_SE_MA = 0x1000
TCP_MA_SE = 0x0100
TCP_CNTL_DATA = 0x0001

TYPE_SE_MA_CNTL = TCP_SE_MA | TCP_CNTL_DATA  # 0x1001
TYPE_MA_SE_CNTL = TCP_MA_SE | TCP_CNTL_DATA  # 0x0101

MSG_CONNECT_ACK = 0x12
MSG_CONNECT_RPT = 0x92

UDP_PORT = 7788
TCP_PORT = 7788
```

- [ ] **Step 4: Create `backend/app/protocol/messages.py`**

```python
import struct
from dataclasses import dataclass

from app.protocol.constants import (
    MSG_CONNECT_ACK,
    MSG_CONNECT_RPT,
    TYPE_MA_SE_CNTL,
    TYPE_SE_MA_CNTL,
)

# Wire format is little-endian per BACS_Control.md (Transmit Ordering column).
_HEADER = struct.Struct("<HH")           # type, length
_CTRL_HEADER = struct.Struct("<HBH")     # node_id, msg_type, msg_len


def build_connect_request(node_id: int = 0) -> bytes:
    ctrl = _CTRL_HEADER.pack(node_id, MSG_CONNECT_ACK, 0)
    header = _HEADER.pack(TYPE_SE_MA_CNTL, len(ctrl))
    return header + ctrl


@dataclass(frozen=True)
class ConnectReply:
    source_id: int
    alive: int


def parse_connect_reply(raw: bytes) -> ConnectReply:
    if len(raw) < _HEADER.size + _CTRL_HEADER.size:
        raise ValueError(f"reply too short: {len(raw)} bytes")
    msg_type, _length = _HEADER.unpack_from(raw, 0)
    if msg_type != TYPE_MA_SE_CNTL:
        raise ValueError(f"unexpected type: 0x{msg_type:04x}")
    source_id, ctrl_type, data_len = _CTRL_HEADER.unpack_from(raw, _HEADER.size)
    if ctrl_type != MSG_CONNECT_RPT:
        raise ValueError(f"unexpected msg_type: 0x{ctrl_type:02x}")
    if data_len != 8:
        raise ValueError(f"unexpected data_len: {data_len}")
    body_start = _HEADER.size + _CTRL_HEADER.size
    (alive,) = struct.unpack_from("<Q", raw, body_start)
    return ConnectReply(source_id=source_id, alive=alive)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend && pytest tests/unit/test_messages.py -v
```

Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/protocol/ backend/tests/unit/test_messages.py
git commit -m "feat(protocol): UDP Connect REQ/RPT pack/unpack with tests"
```

---

### Task 5: UDP client (Heartbeat send/recv)

**Files:**
- Create: `backend/app/protocol/udp_client.py`
- Create: `backend/tests/simulator/__init__.py`
- Create: `backend/tests/simulator/fake_bacs.py`
- Test: `backend/tests/integration/test_udp_heartbeat.py`

- [ ] **Step 1: Create fake BACS UDP simulator (`backend/tests/simulator/fake_bacs.py`)**

```python
import asyncio
import struct

from app.protocol.constants import (
    MSG_CONNECT_RPT,
    TYPE_MA_SE_CNTL,
    TYPE_SE_MA_CNTL,
)


class FakeBacsUdp(asyncio.DatagramProtocol):
    def __init__(self, alive: int = 0xFF) -> None:
        self.alive = alive
        self.transport: asyncio.DatagramTransport | None = None
        self.received: list[bytes] = []

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data: bytes, addr) -> None:
        self.received.append(data)
        msg_type = struct.unpack_from("<H", data, 0)[0]
        if msg_type != TYPE_SE_MA_CNTL:
            return
        ctrl = struct.pack("<HBH", 0, MSG_CONNECT_RPT, 8) + struct.pack("<Q", self.alive)
        header = struct.pack("<HH", TYPE_MA_SE_CNTL, len(ctrl))
        self.transport.sendto(header + ctrl, addr)


async def start_fake_bacs_udp(port: int = 0, alive: int = 0xFF):
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: FakeBacsUdp(alive=alive),
        local_addr=("127.0.0.1", port),
    )
    actual_port = transport.get_extra_info("sockname")[1]
    return transport, protocol, actual_port
```

- [ ] **Step 2: Write the failing test (`backend/tests/integration/test_udp_heartbeat.py`)**

```python
import asyncio

import pytest

from app.protocol.udp_client import heartbeat
from tests.simulator.fake_bacs import start_fake_bacs_udp


@pytest.mark.asyncio
async def test_heartbeat_returns_alive_bitmap_from_fake_bacs():
    transport, _proto, port = await start_fake_bacs_udp(alive=0xABCD)
    try:
        reply = await heartbeat("127.0.0.1", port, timeout=1.0)
        assert reply.alive == 0xABCD
    finally:
        transport.close()


@pytest.mark.asyncio
async def test_heartbeat_times_out_when_no_responder():
    with pytest.raises(asyncio.TimeoutError):
        await heartbeat("127.0.0.1", 1, timeout=0.2)  # nothing listening
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd backend && pytest tests/integration/test_udp_heartbeat.py -v
```

Expected: ImportError (`heartbeat` not defined).

- [ ] **Step 4: Create `backend/app/protocol/udp_client.py`**

```python
import asyncio

from app.protocol.messages import ConnectReply, build_connect_request, parse_connect_reply


class _HeartbeatProtocol(asyncio.DatagramProtocol):
    def __init__(self, future: asyncio.Future) -> None:
        self.future = future
        self.transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data: bytes, addr) -> None:
        if not self.future.done():
            try:
                self.future.set_result(parse_connect_reply(data))
            except ValueError as exc:
                self.future.set_exception(exc)

    def error_received(self, exc):
        if not self.future.done():
            self.future.set_exception(exc)


async def heartbeat(host: str, port: int, *, timeout: float, node_id: int = 0) -> ConnectReply:
    loop = asyncio.get_running_loop()
    future: asyncio.Future[ConnectReply] = loop.create_future()
    transport, _protocol = await loop.create_datagram_endpoint(
        lambda: _HeartbeatProtocol(future),
        remote_addr=(host, port),
    )
    try:
        transport.sendto(build_connect_request(node_id))
        return await asyncio.wait_for(future, timeout=timeout)
    finally:
        transport.close()
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend && pytest tests/integration/test_udp_heartbeat.py -v
```

Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/protocol/udp_client.py backend/tests/simulator/ \
        backend/tests/integration/test_udp_heartbeat.py
git commit -m "feat(protocol): UDP heartbeat client + fake BACS simulator"
```

---

### Task 6: CrossTestProtocol interface + stub

**Files:**
- Create: `backend/app/protocol/crosstest_proto.py`

- [ ] **Step 1: Create `backend/app/protocol/crosstest_proto.py`**

The real BACS↔BACS exchange is TBD per spec §5. The interface and stub below are intentionally placeholder: stub returns `ok` after a short sleep so the scheduler can be developed and tested before the real protocol lands.

```python
import asyncio
import random
from dataclasses import dataclass
from typing import Protocol

from app.models import BacsDevice


@dataclass(frozen=True)
class PairResult:
    ok: bool
    error_message: str | None = None


class CrossTestProtocol(Protocol):
    async def run_pair(
        self, src: BacsDevice, dst: BacsDevice, timeout: float
    ) -> PairResult: ...


class StubCrossTestProtocol:
    """Placeholder until BACS↔BACS call-test message format is finalized.

    Returns ok after 30s, fail after 60s, randomly weighted. Used in dev/tests
    to exercise the scheduler. Real implementation replaces this class.
    """

    def __init__(self, fail_rate: float = 0.0, speed_factor: float = 1.0) -> None:
        self.fail_rate = fail_rate
        self.speed_factor = speed_factor

    async def run_pair(
        self, src: BacsDevice, dst: BacsDevice, timeout: float
    ) -> PairResult:
        will_fail = random.random() < self.fail_rate
        wait = (60.0 if will_fail else 30.0) / self.speed_factor
        try:
            await asyncio.wait_for(asyncio.sleep(wait), timeout=timeout)
        except asyncio.TimeoutError:
            return PairResult(ok=False, error_message="pair timeout")
        if will_fail:
            return PairResult(ok=False, error_message="simulated failure")
        return PairResult(ok=True)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/protocol/crosstest_proto.py
git commit -m "feat(protocol): CrossTestProtocol interface and stub implementation"
```

---

## Phase 3: Health-check service

### Task 7: Repositories (device + health)

**Files:**
- Create: `backend/app/repositories/__init__.py`
- Create: `backend/app/repositories/device_repo.py`
- Create: `backend/app/repositories/health_repo.py`

- [ ] **Step 1: Create `backend/app/repositories/device_repo.py`**

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BacsDevice


async def list_enabled(session: AsyncSession) -> list[BacsDevice]:
    result = await session.execute(select(BacsDevice).where(BacsDevice.enabled.is_(True)))
    return list(result.scalars().all())


async def list_all(session: AsyncSession) -> list[BacsDevice]:
    result = await session.execute(select(BacsDevice))
    return list(result.scalars().all())


async def get_by_ids(session: AsyncSession, ids: list[int]) -> list[BacsDevice]:
    if not ids:
        return []
    result = await session.execute(select(BacsDevice).where(BacsDevice.id.in_(ids)))
    return list(result.scalars().all())
```

- [ ] **Step 2: Create `backend/app/repositories/health_repo.py`**

```python
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DeviceHealth, HealthStatus


async def upsert(
    session: AsyncSession,
    *,
    bacs_id: int,
    status: HealthStatus,
    checked_at: datetime,
    error: str | None,
) -> None:
    stmt = mysql_insert(DeviceHealth).values(
        bacs_id=bacs_id,
        status=status,
        last_checked_at=checked_at,
        last_ok_at=checked_at if status == HealthStatus.ok else None,
        last_error=error,
        consecutive_fail=0 if status == HealthStatus.ok else 1,
    )
    existing = await session.get(DeviceHealth, bacs_id)
    if existing is None:
        await session.execute(stmt)
    else:
        existing.status = status
        existing.last_checked_at = checked_at
        if status == HealthStatus.ok:
            existing.last_ok_at = checked_at
            existing.consecutive_fail = 0
            existing.last_error = None
        else:
            existing.consecutive_fail += 1
            existing.last_error = error
    await session.flush()


async def list_all(session: AsyncSession) -> list[DeviceHealth]:
    result = await session.execute(select(DeviceHealth))
    return list(result.scalars().all())
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/repositories/
git commit -m "feat(repo): device and health repositories"
```

---

### Task 8: Health service + scheduler integration

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/health_service.py`
- Test: `backend/tests/integration/test_health_flow.py`

- [ ] **Step 1: Write the failing test (`backend/tests/integration/test_health_flow.py`)**

```python
import asyncio

import pytest

from app.models import BacsDevice, DeviceHealth, HealthStatus
from app.services.health_service import HealthCheckService
from tests.simulator.fake_bacs import start_fake_bacs_udp


@pytest.mark.asyncio
async def test_health_check_marks_responding_device_ok(db_session):
    transport, _proto, port = await start_fake_bacs_udp()
    try:
        device = BacsDevice(name="t1", node_id=0, ip_address="127.0.0.1", udp_port=port)
        db_session.add(device)
        await db_session.commit()
        await db_session.refresh(device)

        svc = HealthCheckService(timeout=1.0, concurrency=4)
        await svc.run_once(db_session)

        health = await db_session.get(DeviceHealth, device.id)
        assert health is not None
        assert health.status == HealthStatus.ok
    finally:
        transport.close()


@pytest.mark.asyncio
async def test_health_check_marks_unreachable_device_fail(db_session):
    device = BacsDevice(name="dead", node_id=0, ip_address="127.0.0.1", udp_port=1)
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)

    svc = HealthCheckService(timeout=0.2, concurrency=4)
    await svc.run_once(db_session)

    health = await db_session.get(DeviceHealth, device.id)
    assert health.status == HealthStatus.fail
```

- [ ] **Step 2: Add test DB fixture in `backend/tests/conftest.py`**

```python
import asyncio
import os

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import Base


TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL", "mysql+aiomysql://ncvs:ncvs@localhost:3306/ncvs_test"
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine(TEST_DB_URL)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine):
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()
```

Note: Run `docker exec -it $(docker compose ps -q mysql) mysql -uroot -proot -e 'CREATE DATABASE IF NOT EXISTS ncvs_test'` once before running tests.

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd backend && pytest tests/integration/test_health_flow.py -v
```

Expected: ImportError on `HealthCheckService`.

- [ ] **Step 4: Create `backend/app/services/health_service.py`**

```python
import asyncio
from datetime import datetime

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BacsDevice, HealthStatus
from app.protocol.udp_client import heartbeat
from app.repositories import device_repo, health_repo


class HealthCheckService:
    def __init__(self, *, timeout: float, concurrency: int) -> None:
        self.timeout = timeout
        self.semaphore = asyncio.Semaphore(concurrency)

    async def _check_one(self, device: BacsDevice) -> tuple[int, HealthStatus, str | None]:
        async with self.semaphore:
            try:
                await heartbeat(device.ip_address, device.udp_port, timeout=self.timeout)
                return device.id, HealthStatus.ok, None
            except asyncio.TimeoutError:
                return device.id, HealthStatus.fail, "timeout"
            except Exception as exc:  # noqa: BLE001
                return device.id, HealthStatus.fail, str(exc)[:255]

    async def run_once(self, session: AsyncSession) -> None:
        devices = await device_repo.list_enabled(session)
        logger.info("health_check.tick devices={}", len(devices))
        results = await asyncio.gather(*(self._check_one(d) for d in devices))
        now = datetime.utcnow()
        for bacs_id, status, error in results:
            await health_repo.upsert(
                session, bacs_id=bacs_id, status=status, checked_at=now, error=error
            )
        await session.commit()
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend && pytest tests/integration/test_health_flow.py -v
```

Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/health_service.py backend/tests/conftest.py \
        backend/tests/integration/test_health_flow.py
git commit -m "feat(health): periodic UDP heartbeat check with TDD coverage"
```

---

## Phase 4: Cross-test scheduler core (TDD)

### Task 9: DeviceLocker

**Files:**
- Create: `backend/app/services/crosstest/__init__.py`
- Create: `backend/app/services/crosstest/device_locker.py`
- Test: `backend/tests/unit/test_device_locker.py`

- [ ] **Step 1: Write the failing test (`backend/tests/unit/test_device_locker.py`)**

```python
import asyncio

import pytest

from app.services.crosstest.device_locker import DeviceLocker


@pytest.mark.asyncio
async def test_acquire_pair_succeeds_when_both_free():
    locker = DeviceLocker()
    assert await locker.try_acquire_pair(1, 2, session_id=10) is True
    assert locker.is_locked(1) and locker.is_locked(2)


@pytest.mark.asyncio
async def test_acquire_pair_fails_when_one_locked():
    locker = DeviceLocker()
    await locker.try_acquire_pair(1, 2, session_id=10)
    assert await locker.try_acquire_pair(2, 3, session_id=11) is False
    # device 3 must NOT be left locked
    assert not locker.is_locked(3)


@pytest.mark.asyncio
async def test_release_unblocks_waiters():
    locker = DeviceLocker()
    await locker.try_acquire_pair(1, 2, session_id=10)
    waiter = asyncio.create_task(locker.wait_for_release())
    await asyncio.sleep(0)
    assert not waiter.done()
    await locker.release_pair(1, 2)
    await asyncio.wait_for(waiter, timeout=0.5)


@pytest.mark.asyncio
async def test_acquire_pair_always_orders_lock_acquisition():
    """Ordered acquisition prevents deadlock between (1,2) and (2,1)."""
    locker = DeviceLocker()
    a = locker.try_acquire_pair(1, 2, session_id=10)
    b = locker.try_acquire_pair(2, 1, session_id=11)
    results = await asyncio.gather(a, b)
    # Exactly one must win, never both, never neither (no deadlock).
    assert sum(results) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/unit/test_device_locker.py -v
```

Expected: ImportError.

- [ ] **Step 3: Create `backend/app/services/crosstest/device_locker.py`**

```python
import asyncio


class DeviceLocker:
    """In-process per-device locking with a global release notifier.

    Acquires the two device locks in a deterministic order (sorted by id) to
    avoid deadlocks. try_acquire_pair is non-blocking: it either takes both
    or releases any partial acquisition.
    """

    def __init__(self) -> None:
        self._locks: dict[int, asyncio.Lock] = {}
        self._owners: dict[int, int] = {}
        self._global_lock = asyncio.Lock()
        self._release_event = asyncio.Event()

    def _lock_for(self, bacs_id: int) -> asyncio.Lock:
        if bacs_id not in self._locks:
            self._locks[bacs_id] = asyncio.Lock()
        return self._locks[bacs_id]

    def is_locked(self, bacs_id: int) -> bool:
        lock = self._locks.get(bacs_id)
        return lock is not None and lock.locked()

    async def try_acquire_pair(self, a: int, b: int, *, session_id: int) -> bool:
        first, second = sorted([a, b])
        # Single global section per attempt — guarantees no two callers
        # interleave their lock checks and both succeed.
        async with self._global_lock:
            l1, l2 = self._lock_for(first), self._lock_for(second)
            if l1.locked() or l2.locked():
                return False
            await l1.acquire()
            await l2.acquire()
            self._owners[first] = session_id
            self._owners[second] = session_id
            return True

    async def release_pair(self, a: int, b: int) -> None:
        for bacs_id in (a, b):
            lock = self._locks.get(bacs_id)
            if lock and lock.locked():
                lock.release()
            self._owners.pop(bacs_id, None)
        self._release_event.set()
        self._release_event.clear()

    async def wait_for_release(self) -> None:
        await self._release_event.wait()

    def locked_devices(self) -> set[int]:
        return {bid for bid, lock in self._locks.items() if lock.locked()}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/unit/test_device_locker.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/crosstest/device_locker.py \
        backend/app/services/crosstest/__init__.py \
        backend/tests/unit/test_device_locker.py
git commit -m "feat(crosstest): DeviceLocker with deadlock-free pair acquisition"
```

---

### Task 10: Pair repository

**Files:**
- Create: `backend/app/repositories/session_repo.py`
- Create: `backend/app/repositories/pair_repo.py`
- Create: `backend/app/repositories/lock_repo.py`

- [ ] **Step 1: Create `backend/app/repositories/session_repo.py`**

```python
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SessionStatus, TestSession


async def create(
    session: AsyncSession, *, user_id: int, device_ids: list[int], total_pairs: int
) -> TestSession:
    obj = TestSession(
        user_id=user_id,
        device_ids=device_ids,
        total_pairs=total_pairs,
        status=SessionStatus.queued,
        started_at=datetime.utcnow(),
    )
    session.add(obj)
    await session.flush()
    return obj


async def get(session: AsyncSession, session_id: int) -> TestSession | None:
    return await session.get(TestSession, session_id)


async def list_active(session: AsyncSession) -> list[TestSession]:
    result = await session.execute(
        select(TestSession).where(
            TestSession.status.in_([SessionStatus.queued, SessionStatus.running])
        )
    )
    return list(result.scalars().all())


async def mark_running(session: AsyncSession, session_id: int) -> None:
    obj = await session.get(TestSession, session_id)
    if obj is not None:
        obj.status = SessionStatus.running


async def mark_finished(
    session: AsyncSession, session_id: int, status: SessionStatus
) -> None:
    obj = await session.get(TestSession, session_id)
    if obj is not None:
        obj.status = status
        obj.finished_at = datetime.utcnow()


async def increment_counters(
    session: AsyncSession, session_id: int, *, ok: bool
) -> None:
    obj = await session.get(TestSession, session_id)
    if obj is None:
        return
    obj.done_pairs += 1
    if ok:
        obj.ok_pairs += 1
    else:
        obj.fail_pairs += 1
```

- [ ] **Step 2: Create `backend/app/repositories/pair_repo.py`**

```python
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    PairLatestResult,
    PairLatestStatus,
    PairStatus,
    TestSessionPair,
)


async def bulk_insert_pending(
    session: AsyncSession, session_id: int, ordered_pairs: list[tuple[int, int]]
) -> None:
    session.add_all(
        TestSessionPair(
            session_id=session_id, src_bacs_id=src, dst_bacs_id=dst, status=PairStatus.pending
        )
        for src, dst in ordered_pairs
    )
    await session.flush()


async def list_pending_for_session(
    session: AsyncSession, session_id: int
) -> list[TestSessionPair]:
    result = await session.execute(
        select(TestSessionPair).where(
            TestSessionPair.session_id == session_id,
            TestSessionPair.status == PairStatus.pending,
        )
    )
    return list(result.scalars().all())


async def list_running(session: AsyncSession, session_id: int) -> list[TestSessionPair]:
    result = await session.execute(
        select(TestSessionPair).where(
            TestSessionPair.session_id == session_id,
            TestSessionPair.status == PairStatus.running,
        )
    )
    return list(result.scalars().all())


async def mark_running(session: AsyncSession, pair_id: int) -> None:
    obj = await session.get(TestSessionPair, pair_id)
    if obj is not None:
        obj.status = PairStatus.running
        obj.started_at = datetime.utcnow()


async def mark_result(
    session: AsyncSession, pair_id: int, *, ok: bool, error: str | None
) -> None:
    obj = await session.get(TestSessionPair, pair_id)
    if obj is None:
        return
    obj.status = PairStatus.ok if ok else PairStatus.fail
    obj.finished_at = datetime.utcnow()
    obj.error_message = error


async def upsert_latest(
    session: AsyncSession,
    *,
    src_bacs_id: int,
    dst_bacs_id: int,
    ok: bool,
    error: str | None,
    session_id: int,
) -> None:
    existing = await session.get(PairLatestResult, (src_bacs_id, dst_bacs_id))
    status = PairLatestStatus.ok if ok else PairLatestStatus.fail
    now = datetime.utcnow()
    if existing is None:
        session.add(
            PairLatestResult(
                src_bacs_id=src_bacs_id,
                dst_bacs_id=dst_bacs_id,
                status=status,
                tested_at=now,
                session_id=session_id,
                error_message=error,
            )
        )
    else:
        existing.status = status
        existing.tested_at = now
        existing.session_id = session_id
        existing.error_message = error
    await session.flush()
```

- [ ] **Step 3: Create `backend/app/repositories/lock_repo.py`**

```python
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DeviceLock


async def add(session: AsyncSession, bacs_id: int, session_id: int) -> None:
    session.add(DeviceLock(bacs_id=bacs_id, session_id=session_id))
    await session.flush()


async def remove(session: AsyncSession, bacs_id: int) -> None:
    await session.execute(delete(DeviceLock).where(DeviceLock.bacs_id == bacs_id))
    await session.flush()


async def clear_all(session: AsyncSession) -> None:
    await session.execute(delete(DeviceLock))
    await session.flush()
```

- [ ] **Step 4: Create `backend/app/repositories/__init__.py`**

```python
from app.repositories import device_repo, health_repo, lock_repo, pair_repo, session_repo

__all__ = ["device_repo", "health_repo", "lock_repo", "pair_repo", "session_repo"]
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/repositories/
git commit -m "feat(repo): session, pair, lock repositories"
```

---

### Task 11: Scheduler dispatch logic (`pick_next_dispatchable`)

**Files:**
- Create: `backend/app/services/crosstest/scheduler.py` (partial — just pick logic)
- Test: `backend/tests/unit/test_scheduler_pick.py`

- [ ] **Step 1: Write the failing test (`backend/tests/unit/test_scheduler_pick.py`)**

```python
from dataclasses import dataclass

from app.services.crosstest.scheduler import pick_next_dispatchable


@dataclass
class _P:
    id: int
    src: int
    dst: int


def test_picks_first_pair_when_no_locks():
    pairs = [_P(1, 10, 20), _P(2, 30, 40)]
    chosen = pick_next_dispatchable(pairs, locked_devices=set())
    assert chosen is not None
    assert chosen.id == 1


def test_skips_pairs_that_touch_locked_device():
    pairs = [_P(1, 10, 20), _P(2, 30, 40)]
    chosen = pick_next_dispatchable(pairs, locked_devices={10})
    assert chosen.id == 2


def test_returns_none_when_all_blocked():
    pairs = [_P(1, 10, 20), _P(2, 10, 30)]
    chosen = pick_next_dispatchable(pairs, locked_devices={10})
    assert chosen is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/unit/test_scheduler_pick.py -v
```

Expected: ImportError.

- [ ] **Step 3: Create `backend/app/services/crosstest/scheduler.py` (pick fn only)**

```python
from typing import Protocol


class _PairLike(Protocol):
    id: int
    src_bacs_id: int
    dst_bacs_id: int


def pick_next_dispatchable(pairs, locked_devices: set[int]):
    """Return the first pair whose src and dst are both unlocked, or None."""
    for pair in pairs:
        src = getattr(pair, "src_bacs_id", None) or getattr(pair, "src", None)
        dst = getattr(pair, "dst_bacs_id", None) or getattr(pair, "dst", None)
        if src in locked_devices or dst in locked_devices:
            continue
        return pair
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/unit/test_scheduler_pick.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/crosstest/scheduler.py \
        backend/tests/unit/test_scheduler_pick.py
git commit -m "feat(crosstest): pair-dispatch pick logic with TDD"
```

---

### Task 12: Full CrossTestScheduler (dispatch loop + worker)

**Files:**
- Modify: `backend/app/services/crosstest/scheduler.py`
- Create: `backend/app/services/crosstest/runner.py`

- [ ] **Step 1: Create `backend/app/services/crosstest/runner.py`**

```python
import asyncio
from dataclasses import dataclass

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.protocol.crosstest_proto import CrossTestProtocol, PairResult
from app.repositories import lock_repo, pair_repo, session_repo


@dataclass
class WorkItem:
    pair_id: int
    session_id: int
    src_id: int
    dst_id: int


class PairRunner:
    def __init__(
        self,
        proto: CrossTestProtocol,
        session_factory: async_sessionmaker[AsyncSession],
        pair_timeout: float,
    ) -> None:
        self.proto = proto
        self.session_factory = session_factory
        self.pair_timeout = pair_timeout

    async def run(self, item: WorkItem, src, dst) -> PairResult:
        async with self.session_factory() as db:
            await pair_repo.mark_running(db, item.pair_id)
            await db.commit()

        logger.info("crosstest.pair.start session={} pair={}", item.session_id, item.pair_id)
        try:
            result = await self.proto.run_pair(src, dst, timeout=self.pair_timeout)
        except asyncio.TimeoutError:
            result = PairResult(ok=False, error_message="pair timeout")
        except Exception as exc:  # noqa: BLE001
            result = PairResult(ok=False, error_message=str(exc)[:255])

        async with self.session_factory() as db:
            await pair_repo.mark_result(
                db, item.pair_id, ok=result.ok, error=result.error_message
            )
            await pair_repo.upsert_latest(
                db,
                src_bacs_id=item.src_id,
                dst_bacs_id=item.dst_id,
                ok=result.ok,
                error=result.error_message,
                session_id=item.session_id,
            )
            await session_repo.increment_counters(db, item.session_id, ok=result.ok)
            await lock_repo.remove(db, item.src_id)
            await lock_repo.remove(db, item.dst_id)
            await db.commit()

        logger.info(
            "crosstest.pair.{} session={} pair={}",
            "ok" if result.ok else "fail",
            item.session_id,
            item.pair_id,
        )
        return result
```

- [ ] **Step 2: Replace `backend/app/services/crosstest/scheduler.py` with full impl**

```python
import asyncio

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import BacsDevice, SessionStatus
from app.repositories import device_repo, lock_repo, pair_repo, session_repo
from app.services.crosstest.device_locker import DeviceLocker
from app.services.crosstest.runner import PairRunner, WorkItem


def pick_next_dispatchable(pairs, locked_devices: set[int]):
    for pair in pairs:
        src = getattr(pair, "src_bacs_id", None) or getattr(pair, "src", None)
        dst = getattr(pair, "dst_bacs_id", None) or getattr(pair, "dst", None)
        if src in locked_devices or dst in locked_devices:
            continue
        return pair
    return None


class CrossTestScheduler:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        runner: PairRunner,
        *,
        max_concurrent_pairs: int,
        dispatch_interval_ms: int,
    ) -> None:
        self.session_factory = session_factory
        self.runner = runner
        self.locker = DeviceLocker()
        self.semaphore = asyncio.Semaphore(max_concurrent_pairs)
        self.dispatch_interval = dispatch_interval_ms / 1000.0
        self._queued_sessions: asyncio.Queue[int] = asyncio.Queue()
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    def submit(self, session_id: int) -> None:
        self._queued_sessions.put_nowait(session_id)

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._main_loop())

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            await self._task

    async def _main_loop(self) -> None:
        active: set[asyncio.Task] = set()
        while not self._stop.is_set():
            try:
                sid = await asyncio.wait_for(self._queued_sessions.get(), timeout=0.5)
            except asyncio.TimeoutError:
                # opportunistically prune finished worker tasks
                active = {t for t in active if not t.done()}
                continue
            session_task = asyncio.create_task(self._run_session(sid))
            active.add(session_task)
            session_task.add_done_callback(active.discard)

    async def _run_session(self, session_id: int) -> None:
        logger.info("crosstest.session.start session={}", session_id)
        async with self.session_factory() as db:
            await session_repo.mark_running(db, session_id)
            await db.commit()

        in_flight: set[asyncio.Task] = set()

        while True:
            async with self.session_factory() as db:
                pending = await pair_repo.list_pending_for_session(db, session_id)
            if not pending and not in_flight:
                break

            chosen = pick_next_dispatchable(pending, self.locker.locked_devices())
            if chosen is None:
                if in_flight:
                    done, in_flight = await asyncio.wait(
                        in_flight, return_when=asyncio.FIRST_COMPLETED
                    )
                else:
                    try:
                        await asyncio.wait_for(
                            self.locker.wait_for_release(), timeout=self.dispatch_interval
                        )
                    except asyncio.TimeoutError:
                        pass
                continue

            acquired = await self.locker.try_acquire_pair(
                chosen.src_bacs_id, chosen.dst_bacs_id, session_id=session_id
            )
            if not acquired:
                continue

            async with self.session_factory() as db:
                await lock_repo.add(db, chosen.src_bacs_id, session_id)
                await lock_repo.add(db, chosen.dst_bacs_id, session_id)
                await db.commit()
                devices = await device_repo.get_by_ids(
                    db, [chosen.src_bacs_id, chosen.dst_bacs_id]
                )
            by_id: dict[int, BacsDevice] = {d.id: d for d in devices}
            item = WorkItem(
                pair_id=chosen.id,
                session_id=session_id,
                src_id=chosen.src_bacs_id,
                dst_id=chosen.dst_bacs_id,
            )

            async def _worker_wrapper(it=item, src=by_id[chosen.src_bacs_id],
                                      dst=by_id[chosen.dst_bacs_id]):
                async with self.semaphore:
                    try:
                        await self.runner.run(it, src, dst)
                    finally:
                        await self.locker.release_pair(it.src_id, it.dst_id)

            in_flight.add(asyncio.create_task(_worker_wrapper()))

        async with self.session_factory() as db:
            await session_repo.mark_finished(db, session_id, SessionStatus.completed)
            await db.commit()
        logger.info("crosstest.session.complete session={}", session_id)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/crosstest/scheduler.py \
        backend/app/services/crosstest/runner.py
git commit -m "feat(crosstest): scheduler dispatch loop and pair runner"
```

---

### Task 13: SessionService + end-to-end cross-test integration test

**Files:**
- Create: `backend/app/services/session_service.py`
- Test: `backend/tests/integration/test_crosstest_flow.py`

- [ ] **Step 1: Create `backend/app/services/session_service.py`**

```python
from itertools import permutations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SessionStatus, TestSession
from app.repositories import pair_repo, session_repo


async def create_session(
    session: AsyncSession, *, user_id: int, device_ids: list[int]
) -> TestSession:
    if len(device_ids) < 2:
        raise ValueError("at least 2 devices required")
    ordered_pairs = list(permutations(device_ids, 2))  # (src, dst) directed pairs
    test_session = await session_repo.create(
        session,
        user_id=user_id,
        device_ids=device_ids,
        total_pairs=len(ordered_pairs),
    )
    await pair_repo.bulk_insert_pending(session, test_session.id, ordered_pairs)
    await session.commit()
    return test_session


async def cancel_session(session: AsyncSession, session_id: int) -> None:
    await session_repo.mark_finished(session, session_id, SessionStatus.cancelled)
    await session.commit()
```

- [ ] **Step 2: Write the failing test (`backend/tests/integration/test_crosstest_flow.py`)**

```python
import asyncio

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models import BacsDevice, PairLatestResult, SessionStatus, TestSession, User
from app.protocol.crosstest_proto import StubCrossTestProtocol
from app.services.crosstest.runner import PairRunner
from app.services.crosstest.scheduler import CrossTestScheduler
from app.services.session_service import create_session


@pytest.mark.asyncio
async def test_full_crosstest_run_completes_all_pairs(engine, db_session):
    user = User(username="u", password_hash="x")
    db_session.add(user)
    devices = [
        BacsDevice(name=f"b{i}", node_id=i, ip_address=f"127.0.0.{i+10}") for i in range(3)
    ]
    db_session.add_all(devices)
    await db_session.commit()
    for d in devices:
        await db_session.refresh(d)
    await db_session.refresh(user)

    ts = await create_session(
        db_session, user_id=user.id, device_ids=[d.id for d in devices]
    )

    factory = async_sessionmaker(engine, expire_on_commit=False)
    runner = PairRunner(StubCrossTestProtocol(speed_factor=300.0), factory, pair_timeout=5.0)
    scheduler = CrossTestScheduler(
        factory, runner, max_concurrent_pairs=4, dispatch_interval_ms=50
    )
    scheduler.start()
    scheduler.submit(ts.id)

    for _ in range(200):
        await asyncio.sleep(0.1)
        async with factory() as s:
            obj = await s.get(TestSession, ts.id)
            if obj.status == SessionStatus.completed:
                break
    else:
        pytest.fail("session did not complete in time")

    await scheduler.stop()

    async with factory() as s:
        obj = await s.get(TestSession, ts.id)
        assert obj.status == SessionStatus.completed
        assert obj.done_pairs == 6  # 3*2 directed pairs
        assert obj.ok_pairs == 6
```

- [ ] **Step 3: Run test to verify it passes**

```bash
cd backend && pytest tests/integration/test_crosstest_flow.py -v
```

Expected: 1 passed (may take ~5s due to 30s/300x sim sleep).

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/session_service.py \
        backend/tests/integration/test_crosstest_flow.py
git commit -m "feat(crosstest): session service and end-to-end integration test"
```

---

### Task 14: Concurrent multi-session lock-respect test

**Files:**
- Test: `backend/tests/integration/test_concurrent_sessions.py`

- [ ] **Step 1: Write the test**

```python
import asyncio

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models import BacsDevice, PairStatus, SessionStatus, TestSession, TestSessionPair, User
from app.protocol.crosstest_proto import StubCrossTestProtocol
from app.services.crosstest.runner import PairRunner
from app.services.crosstest.scheduler import CrossTestScheduler
from app.services.session_service import create_session


@pytest.mark.asyncio
async def test_overlapping_sessions_never_share_device_simultaneously(engine, db_session):
    user = User(username="u2", password_hash="x")
    db_session.add(user)
    devices = [BacsDevice(name=f"b{i}", node_id=i, ip_address=f"127.0.0.{i+50}") for i in range(4)]
    db_session.add_all(devices)
    await db_session.commit()
    for d in devices:
        await db_session.refresh(d)
    await db_session.refresh(user)

    # Session A: devices 0,1  ; Session B: devices 1,2  (device 1 overlaps)
    sa = await create_session(db_session, user_id=user.id, device_ids=[devices[0].id, devices[1].id])
    sb = await create_session(db_session, user_id=user.id, device_ids=[devices[1].id, devices[2].id])

    factory = async_sessionmaker(engine, expire_on_commit=False)
    runner = PairRunner(StubCrossTestProtocol(speed_factor=300.0), factory, pair_timeout=5.0)
    scheduler = CrossTestScheduler(factory, runner, max_concurrent_pairs=8, dispatch_interval_ms=20)
    scheduler.start()
    scheduler.submit(sa.id)
    scheduler.submit(sb.id)

    # Poll: at no observation point may a device-1-touching pair be 'running' in both sessions.
    for _ in range(200):
        await asyncio.sleep(0.05)
        async with factory() as s:
            run_a = [
                p for p in (await s.execute(
                    TestSessionPair.__table__.select().where(
                        TestSessionPair.session_id == sa.id,
                        TestSessionPair.status == PairStatus.running,
                    )
                )).all()
            ]
            run_b = [
                p for p in (await s.execute(
                    TestSessionPair.__table__.select().where(
                        TestSessionPair.session_id == sb.id,
                        TestSessionPair.status == PairStatus.running,
                    )
                )).all()
            ]
            devices_in_flight = set()
            for row in run_a + run_b:
                devices_in_flight.add(row.src_bacs_id)
                devices_in_flight.add(row.dst_bacs_id)
            # invariant: total running pair count == unique devices / 2 (no device appears twice)
            assert len(devices_in_flight) == 2 * (len(run_a) + len(run_b))

    # both sessions eventually complete
    for _ in range(200):
        await asyncio.sleep(0.1)
        async with factory() as s:
            a = await s.get(TestSession, sa.id)
            b = await s.get(TestSession, sb.id)
            if a.status == SessionStatus.completed and b.status == SessionStatus.completed:
                break
    else:
        pytest.fail("sessions did not complete")
    await scheduler.stop()
```

- [ ] **Step 2: Run and verify pass**

```bash
cd backend && pytest tests/integration/test_concurrent_sessions.py -v
```

Expected: PASS. (If fails, investigate scheduler — invariant violation indicates lock race.)

- [ ] **Step 3: Commit**

```bash
git add backend/tests/integration/test_concurrent_sessions.py
git commit -m "test(crosstest): verify device-lock invariant across overlapping sessions"
```

---

## Phase 5: Auth + API layer

### Task 15: Security helpers

**Files:**
- Create: `backend/app/security.py`
- Create: `backend/app/repositories/user_repo.py`
- Test: `backend/tests/unit/test_security.py`

- [ ] **Step 1: Write the failing test**

```python
from datetime import timedelta

from app.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_roundtrip():
    h = hash_password("secret")
    assert verify_password("secret", h)
    assert not verify_password("wrong", h)


def test_jwt_roundtrip():
    token = create_access_token(subject="42", expires_delta=timedelta(minutes=5))
    payload = decode_access_token(token)
    assert payload["sub"] == "42"
```

- [ ] **Step 2: Create `backend/app/security.py`**

```python
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.config import settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


def create_access_token(*, subject: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    )
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
```

- [ ] **Step 3: Create `backend/app/repositories/user_repo.py`**

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


async def get_by_username(session: AsyncSession, username: str) -> User | None:
    result = await session.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def create(session: AsyncSession, *, username: str, password_hash: str) -> User:
    obj = User(username=username, password_hash=password_hash)
    session.add(obj)
    await session.flush()
    return obj
```

- [ ] **Step 4: Run tests**

```bash
cd backend && pytest tests/unit/test_security.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/security.py backend/app/repositories/user_repo.py \
        backend/tests/unit/test_security.py
git commit -m "feat(security): password hashing and JWT helpers"
```

---

### Task 16: FastAPI app + auth dependency + auth routes

**Files:**
- Create: `backend/app/deps.py`
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/auth.py`
- Create: `backend/app/main.py`

- [ ] **Step 1: Create `backend/app/schemas/auth.py`**

```python
from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
```

- [ ] **Step 2: Create `backend/app/deps.py`**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import User
from app.repositories import user_repo
from app.security import decode_access_token

oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(oauth2), session: AsyncSession = Depends(get_session)
) -> User:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials"
    )
    try:
        payload = decode_access_token(token)
        username = payload.get("sub")
    except InvalidTokenError as exc:
        raise cred_exc from exc
    if not username:
        raise cred_exc
    user = await user_repo.get_by_username(session, username)
    if user is None:
        raise cred_exc
    return user
```

- [ ] **Step 3: Create `backend/app/api/auth.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.repositories import user_repo
from app.schemas.auth import LoginRequest, TokenResponse
from app.security import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)):
    user = await user_repo.get_by_username(session, body.username)
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
    return TokenResponse(access_token=create_access_token(subject=user.username))
```

- [ ] **Step 4: Create `backend/app/main.py`**

```python
import asyncio
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI
from loguru import logger

from app.api import auth as auth_api
from app.config import settings
from app.db import SessionLocal
from app.models import SessionStatus
from app.protocol.crosstest_proto import StubCrossTestProtocol
from app.repositories import lock_repo, session_repo
from app.services.crosstest.runner import PairRunner
from app.services.crosstest.scheduler import CrossTestScheduler
from app.services.health_service import HealthCheckService


async def _periodic_health(svc: HealthCheckService) -> None:
    async with SessionLocal() as db:
        await svc.run_once(db)


async def _recover_state() -> None:
    async with SessionLocal() as db:
        await lock_repo.clear_all(db)
        active = await session_repo.list_active(db)
        for s in active:
            await session_repo.mark_finished(db, s.id, SessionStatus.failed)
        await db.commit()
        logger.info("startup.recovery cleared_sessions={}", len(active))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _recover_state()

    health_svc = HealthCheckService(
        timeout=settings.HEALTH_CHECK_TIMEOUT_SEC,
        concurrency=settings.HEALTH_CHECK_CONCURRENCY,
    )
    app.state.health_svc = health_svc

    proto = StubCrossTestProtocol()  # replace when real proto is ready
    runner = PairRunner(proto, SessionLocal, pair_timeout=settings.CROSSTEST_PAIR_TIMEOUT_SEC)
    scheduler = CrossTestScheduler(
        SessionLocal,
        runner,
        max_concurrent_pairs=settings.CROSSTEST_MAX_CONCURRENT_PAIRS,
        dispatch_interval_ms=settings.CROSSTEST_DISPATCH_INTERVAL_MS,
    )
    scheduler.start()
    app.state.crosstest = scheduler

    aps = AsyncIOScheduler()
    aps.add_job(
        _periodic_health,
        IntervalTrigger(seconds=settings.HEALTH_CHECK_INTERVAL_SEC),
        args=[health_svc],
        next_run_time=None,
    )
    aps.start()
    app.state.aps = aps
    logger.info("startup.complete")

    yield

    aps.shutdown(wait=False)
    await scheduler.stop()
    logger.info("shutdown.complete")


app = FastAPI(title="NCVS BACS Monitor", lifespan=lifespan)
app.include_router(auth_api.router)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
```

- [ ] **Step 5: Smoke run**

```bash
cd backend && uvicorn app.main:app --reload --port 8000
```

In another shell:
```bash
curl http://localhost:8000/healthz
```

Expected: `{"status":"ok"}`. Stop the server (Ctrl-C).

- [ ] **Step 6: Commit**

```bash
git add backend/app/deps.py backend/app/schemas/auth.py \
        backend/app/api/__init__.py backend/app/api/auth.py backend/app/main.py
git commit -m "feat(api): FastAPI app with auth and lifespan-managed services"
```

---

### Task 17: Device / health / test / matrix endpoints

**Files:**
- Create: `backend/app/schemas/device.py`
- Create: `backend/app/schemas/health.py`
- Create: `backend/app/schemas/session.py`
- Create: `backend/app/schemas/pair.py`
- Create: `backend/app/api/devices.py`
- Create: `backend/app/api/health.py`
- Create: `backend/app/api/tests.py`
- Create: `backend/app/api/matrix.py`
- Modify: `backend/app/main.py:48` (add new routers)

- [ ] **Step 1: Create `backend/app/schemas/device.py`**

```python
from pydantic import BaseModel, ConfigDict


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    node_id: int
    ip_address: str
    udp_port: int
    tcp_port: int
    location: str | None
    enabled: bool
```

- [ ] **Step 2: Create `backend/app/schemas/health.py`**

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import HealthStatus


class HealthOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    bacs_id: int
    status: HealthStatus
    last_checked_at: datetime | None
    last_ok_at: datetime | None
    last_error: str | None
    consecutive_fail: int
```

- [ ] **Step 3: Create `backend/app/schemas/session.py`**

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import SessionStatus


class CreateSessionRequest(BaseModel):
    device_ids: list[int] = Field(min_length=2)


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: SessionStatus
    device_ids: list[int]
    total_pairs: int
    done_pairs: int
    ok_pairs: int
    fail_pairs: int
    started_at: datetime | None
    finished_at: datetime | None
```

- [ ] **Step 4: Create `backend/app/schemas/pair.py`**

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import PairLatestStatus, PairStatus


class PairOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    src_bacs_id: int
    dst_bacs_id: int
    status: PairStatus
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None


class MatrixCell(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    src_bacs_id: int
    dst_bacs_id: int
    status: PairLatestStatus
    tested_at: datetime
    error_message: str | None
```

- [ ] **Step 5: Create `backend/app/api/devices.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.models import User
from app.repositories import device_repo, health_repo
from app.schemas.device import DeviceOut
from app.schemas.health import HealthOut

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("", response_model=list[DeviceOut])
async def list_devices(
    _: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
):
    return await device_repo.list_all(session)


@router.get("/health", response_model=list[HealthOut])
async def list_health(
    _: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
):
    return await health_repo.list_all(session)
```

- [ ] **Step 6: Create `backend/app/api/health.py`**

```python
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.models import User

router = APIRouter(prefix="/health", tags=["health"])


@router.post("/refresh", status_code=202)
async def refresh(
    request: Request,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await request.app.state.health_svc.run_once(session)
    return {"status": "refreshed"}
```

- [ ] **Step 7: Create `backend/app/api/tests.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.models import User
from app.repositories import pair_repo, session_repo
from app.schemas.pair import PairOut
from app.schemas.session import CreateSessionRequest, SessionOut
from app.services.session_service import cancel_session, create_session

router = APIRouter(prefix="/tests", tags=["tests"])


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def create(
    body: CreateSessionRequest,
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    ts = await create_session(session, user_id=user.id, device_ids=body.device_ids)
    request.app.state.crosstest.submit(ts.id)
    return ts


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
```

- [ ] **Step 8: Create `backend/app/api/matrix.py`**

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.models import PairLatestResult, User
from app.schemas.pair import MatrixCell

router = APIRouter(prefix="/pair-matrix", tags=["matrix"])


@router.get("", response_model=list[MatrixCell])
async def get_matrix(
    device_ids: list[int] = Query(...),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(PairLatestResult).where(
            PairLatestResult.src_bacs_id.in_(device_ids),
            PairLatestResult.dst_bacs_id.in_(device_ids),
        )
    )
    return list(result.scalars().all())
```

- [ ] **Step 9: Wire routers in `backend/app/main.py` (modify the `include_router` block)**

Replace `app.include_router(auth_api.router)` with:

```python
from app.api import auth as auth_api, devices as devices_api, health as health_api, \
    tests as tests_api, matrix as matrix_api

app.include_router(auth_api.router)
app.include_router(devices_api.router)
app.include_router(health_api.router)
app.include_router(tests_api.router)
app.include_router(matrix_api.router)
```

- [ ] **Step 10: Commit**

```bash
git add backend/app/schemas/ backend/app/api/ backend/app/main.py
git commit -m "feat(api): device, health, tests, matrix endpoints"
```

---

### Task 18: Seed CLI for admin user and devices

**Files:**
- Create: `backend/app/cli/__init__.py`
- Create: `backend/app/cli/seed.py`

- [ ] **Step 1: Create `backend/app/cli/seed.py`**

```python
"""Run: python -m app.cli.seed admin admin"""
import asyncio
import sys

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
        # demo devices — replace with real INSERTs in production
        if not await session.get(BacsDevice, 1):
            session.add_all(
                BacsDevice(name=f"BACS-{i:03d}", node_id=i % 64, ip_address=f"10.0.0.{i+1}")
                for i in range(1, 6)
            )
        await session.commit()


if __name__ == "__main__":
    asyncio.run(_seed(sys.argv[1], sys.argv[2]))
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/cli/
git commit -m "feat(cli): seed admin user and demo BACS devices"
```

---

## Phase 6: Frontend (Next.js)

### Task 19: Next.js scaffold + API client

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/next.config.mjs`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/types.ts`
- Create: `frontend/src/app/layout.tsx`

- [ ] **Step 1: Create `frontend/package.json`**

```json
{
  "name": "ncvs-frontend",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  },
  "dependencies": {
    "next": "14.2.3",
    "react": "18.3.1",
    "react-dom": "18.3.1"
  },
  "devDependencies": {
    "@types/node": "20.12.7",
    "@types/react": "18.3.2",
    "typescript": "5.4.5"
  }
}
```

- [ ] **Step 2: Create `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "module": "esnext",
    "moduleResolution": "bundler",
    "jsx": "preserve",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "allowJs": true,
    "noEmit": true,
    "incremental": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "baseUrl": ".",
    "paths": { "@/*": ["src/*"] },
    "plugins": [{ "name": "next" }]
  },
  "include": ["next-env.d.ts", "src/**/*.ts", "src/**/*.tsx"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 3: Create `frontend/next.config.mjs`**

```javascript
const config = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: "http://localhost:8000/:path*" }];
  },
};
export default config;
```

- [ ] **Step 4: Create `frontend/src/lib/types.ts`**

```typescript
export type HealthStatus = "ok" | "fail" | "unknown";
export type SessionStatus = "queued" | "running" | "completed" | "cancelled" | "failed";

export interface Device {
  id: number;
  name: string;
  node_id: number;
  ip_address: string;
  udp_port: number;
  tcp_port: number;
  location: string | null;
  enabled: boolean;
}

export interface Health {
  bacs_id: number;
  status: HealthStatus;
  last_checked_at: string | null;
  last_ok_at: string | null;
  last_error: string | null;
  consecutive_fail: number;
}

export interface Session {
  id: number;
  status: SessionStatus;
  device_ids: number[];
  total_pairs: number;
  done_pairs: number;
  ok_pairs: number;
  fail_pairs: number;
  started_at: string | null;
  finished_at: string | null;
}

export interface MatrixCell {
  src_bacs_id: number;
  dst_bacs_id: number;
  status: "ok" | "fail";
  tested_at: string;
  error_message: string | null;
}
```

- [ ] **Step 5: Create `frontend/src/lib/api.ts`**

```typescript
const TOKEN_KEY = "ncvs_token";

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}
export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string>),
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`/api${path}`, { ...init, headers });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json() as Promise<T>;
}

export const api = {
  login: (username: string, password: string) =>
    request<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  devices: () => request<import("./types").Device[]>("/devices"),
  health: () => request<import("./types").Health[]>("/devices/health"),
  refreshHealth: () => request<{ status: string }>("/health/refresh", { method: "POST" }),
  startTest: (device_ids: number[]) =>
    request<import("./types").Session>("/tests", {
      method: "POST",
      body: JSON.stringify({ device_ids }),
    }),
  session: (id: number) => request<import("./types").Session>(`/tests/${id}`),
  cancelSession: (id: number) =>
    request<{ status: string }>(`/tests/${id}/cancel`, { method: "POST" }),
  matrix: (deviceIds: number[]) => {
    const qs = deviceIds.map((id) => `device_ids=${id}`).join("&");
    return request<import("./types").MatrixCell[]>(`/pair-matrix?${qs}`);
  },
};
```

- [ ] **Step 6: Create `frontend/src/app/layout.tsx`**

```tsx
export const metadata = { title: "NCVS BACS Monitor" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body style={{ fontFamily: "system-ui", margin: 0, padding: 16 }}>{children}</body>
    </html>
  );
}
```

- [ ] **Step 7: Install and verify dev server starts**

```bash
cd frontend && npm install && npm run dev -- --port 3000 &
sleep 5
curl -s http://localhost:3000 -o /dev/null -w "%{http_code}\n"
kill %1
```

Expected: `200`.

- [ ] **Step 8: Commit**

```bash
git add frontend/package.json frontend/tsconfig.json frontend/next.config.mjs \
        frontend/src/lib/ frontend/src/app/layout.tsx
git commit -m "feat(frontend): scaffold Next.js + API client"
```

---

### Task 20: Login page

**Files:**
- Create: `frontend/src/app/login/page.tsx`

- [ ] **Step 1: Create the page**

```tsx
"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { api, setToken } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const { access_token } = await api.login(username, password);
      setToken(access_token);
      router.push("/devices");
    } catch (err: any) {
      setError(err.message);
    }
  }

  return (
    <main style={{ maxWidth: 320 }}>
      <h1>로그인</h1>
      <form onSubmit={submit}>
        <input
          placeholder="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          style={{ display: "block", marginBottom: 8, width: "100%" }}
        />
        <input
          type="password"
          placeholder="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          style={{ display: "block", marginBottom: 8, width: "100%" }}
        />
        <button type="submit">로그인</button>
        {error && <p style={{ color: "red" }}>{error}</p>}
      </form>
    </main>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/login/page.tsx
git commit -m "feat(frontend): login page"
```

---

### Task 21: Devices dashboard (list + health + test trigger)

**Files:**
- Create: `frontend/src/components/HealthBadge.tsx`
- Create: `frontend/src/components/DeviceTable.tsx`
- Create: `frontend/src/app/devices/page.tsx`

- [ ] **Step 1: Create `frontend/src/components/HealthBadge.tsx`**

```tsx
import { HealthStatus } from "@/lib/types";

const COLOR: Record<HealthStatus, string> = {
  ok: "#2ecc71",
  fail: "#e74c3c",
  unknown: "#95a5a6",
};

export function HealthBadge({ status }: { status: HealthStatus }) {
  return (
    <span
      style={{
        background: COLOR[status],
        color: "white",
        padding: "2px 8px",
        borderRadius: 4,
        fontSize: 12,
      }}
    >
      {status}
    </span>
  );
}
```

- [ ] **Step 2: Create `frontend/src/components/DeviceTable.tsx`**

```tsx
import { Device, Health } from "@/lib/types";
import { HealthBadge } from "./HealthBadge";

type Props = {
  devices: Device[];
  health: Map<number, Health>;
  selected: Set<number>;
  onToggle: (id: number) => void;
};

export function DeviceTable({ devices, health, selected, onToggle }: Props) {
  return (
    <table cellPadding={6} style={{ borderCollapse: "collapse", width: "100%" }}>
      <thead>
        <tr style={{ background: "#f4f4f4", textAlign: "left" }}>
          <th></th>
          <th>Name</th>
          <th>IP</th>
          <th>Health</th>
          <th>Last checked</th>
        </tr>
      </thead>
      <tbody>
        {devices.map((d) => {
          const h = health.get(d.id);
          return (
            <tr key={d.id} style={{ borderTop: "1px solid #eee" }}>
              <td>
                <input
                  type="checkbox"
                  checked={selected.has(d.id)}
                  onChange={() => onToggle(d.id)}
                />
              </td>
              <td>{d.name}</td>
              <td>{d.ip_address}</td>
              <td><HealthBadge status={h?.status ?? "unknown"} /></td>
              <td style={{ fontSize: 12, color: "#666" }}>
                {h?.last_checked_at ?? "-"}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
```

- [ ] **Step 3: Create `frontend/src/app/devices/page.tsx`**

```tsx
"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { DeviceTable } from "@/components/DeviceTable";
import { api, getToken } from "@/lib/api";
import { Device, Health } from "@/lib/types";

export default function DevicesPage() {
  const router = useRouter();
  const [devices, setDevices] = useState<Device[]>([]);
  const [health, setHealth] = useState<Map<number, Health>>(new Map());
  const [selected, setSelected] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
  }, [router]);

  const loadHealth = useCallback(async () => {
    const rows = await api.health();
    setHealth(new Map(rows.map((r) => [r.bacs_id, r])));
  }, []);

  useEffect(() => {
    api.devices().then(setDevices);
    loadHealth();
    const t = setInterval(loadHealth, 3000);
    return () => clearInterval(t);
  }, [loadHealth]);

  function toggle(id: number) {
    setSelected((s) => {
      const next = new Set(s);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function startTest() {
    if (selected.size < 2) {
      alert("2개 이상 선택하세요");
      return;
    }
    const session = await api.startTest([...selected]);
    router.push(`/tests/${session.id}`);
  }

  return (
    <main>
      <h1>BACS 장비</h1>
      <div style={{ marginBottom: 12 }}>
        <button onClick={() => api.refreshHealth().then(loadHealth)}>
          Refresh Health
        </button>
        <button onClick={startTest} style={{ marginLeft: 8 }}>
          선택 장비 Cross-test 시작 ({selected.size})
        </button>
      </div>
      <DeviceTable
        devices={devices}
        health={health}
        selected={selected}
        onToggle={toggle}
      />
    </main>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ frontend/src/app/devices/page.tsx
git commit -m "feat(frontend): devices dashboard with health and test trigger"
```

---

### Task 22: Test progress page

**Files:**
- Create: `frontend/src/components/TestProgress.tsx`
- Create: `frontend/src/app/tests/[id]/page.tsx`

- [ ] **Step 1: Create `frontend/src/components/TestProgress.tsx`**

```tsx
import { Session } from "@/lib/types";

export function TestProgress({ s }: { s: Session }) {
  const pct = s.total_pairs === 0 ? 0 : Math.round((s.done_pairs / s.total_pairs) * 100);
  return (
    <div>
      <p>Status: <strong>{s.status}</strong></p>
      <div style={{ background: "#eee", height: 16, borderRadius: 4 }}>
        <div
          style={{
            background: "#3498db",
            height: "100%",
            width: `${pct}%`,
            borderRadius: 4,
          }}
        />
      </div>
      <p>
        {s.done_pairs} / {s.total_pairs} (ok: {s.ok_pairs}, fail: {s.fail_pairs})
      </p>
    </div>
  );
}
```

- [ ] **Step 2: Create `frontend/src/app/tests/[id]/page.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";

import { TestProgress } from "@/components/TestProgress";
import { api } from "@/lib/api";
import { Session } from "@/lib/types";

export default function TestPage({ params }: { params: { id: string } }) {
  const id = Number(params.id);
  const [session, setSession] = useState<Session | null>(null);

  useEffect(() => {
    let active = true;
    async function poll() {
      try {
        const s = await api.session(id);
        if (active) setSession(s);
      } catch {
        /* ignore */
      }
    }
    poll();
    const t = setInterval(poll, 3000);
    return () => {
      active = false;
      clearInterval(t);
    };
  }, [id]);

  if (!session) return <main>로딩…</main>;
  return (
    <main>
      <h1>Test Session #{session.id}</h1>
      <TestProgress s={session} />
      {session.status === "running" && (
        <button onClick={() => api.cancelSession(id)} style={{ marginTop: 12 }}>
          취소
        </button>
      )}
    </main>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/TestProgress.tsx frontend/src/app/tests/
git commit -m "feat(frontend): test session progress page with polling"
```

---

### Task 23: Matrix view

**Files:**
- Create: `frontend/src/components/Matrix.tsx`
- Create: `frontend/src/app/matrix/page.tsx`

- [ ] **Step 1: Create `frontend/src/components/Matrix.tsx`**

```tsx
import { Device, MatrixCell } from "@/lib/types";

type Props = { devices: Device[]; cells: MatrixCell[] };

export function Matrix({ devices, cells }: Props) {
  const lookup = new Map<string, MatrixCell>();
  for (const c of cells) lookup.set(`${c.src_bacs_id}-${c.dst_bacs_id}`, c);

  return (
    <table cellPadding={4} style={{ borderCollapse: "collapse" }}>
      <thead>
        <tr>
          <th></th>
          {devices.map((d) => (
            <th key={d.id} style={{ writingMode: "vertical-rl", fontSize: 11 }}>
              {d.name}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {devices.map((src) => (
          <tr key={src.id}>
            <td style={{ fontSize: 11, fontWeight: 600 }}>{src.name}</td>
            {devices.map((dst) => {
              if (src.id === dst.id)
                return <td key={dst.id} style={{ background: "#222" }} />;
              const cell = lookup.get(`${src.id}-${dst.id}`);
              const color = cell
                ? cell.status === "ok"
                  ? "#2ecc71"
                  : "#e74c3c"
                : "#bdc3c7";
              return (
                <td
                  key={dst.id}
                  title={cell?.error_message ?? cell?.tested_at ?? "no data"}
                  style={{ background: color, width: 16, height: 16 }}
                />
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

- [ ] **Step 2: Create `frontend/src/app/matrix/page.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";

import { Matrix } from "@/components/Matrix";
import { api } from "@/lib/api";
import { Device, MatrixCell } from "@/lib/types";

export default function MatrixPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [cells, setCells] = useState<MatrixCell[]>([]);

  useEffect(() => {
    api.devices().then(async (ds) => {
      setDevices(ds);
      if (ds.length > 0) setCells(await api.matrix(ds.map((d) => d.id)));
    });
  }, []);

  return (
    <main>
      <h1>Cross-test 결과 매트릭스</h1>
      <p style={{ fontSize: 12, color: "#666" }}>
        행 = 송신(src), 열 = 수신(dst). 녹색 ok / 빨강 fail / 회색 미테스트.
      </p>
      <Matrix devices={devices} cells={cells} />
    </main>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Matrix.tsx frontend/src/app/matrix/
git commit -m "feat(frontend): cross-test result matrix view"
```

---

## Phase 7: Containerization & smoke

### Task 24: Dockerfiles + final compose wiring

**Files:**
- Create: `backend/Dockerfile`
- Create: `frontend/Dockerfile`

- [ ] **Step 1: Create `backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir uv && uv pip install --system .
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Create `frontend/Dockerfile`**

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

- [ ] **Step 3: Smoke run full stack**

```bash
docker compose up -d --build
sleep 20
# Apply migrations inside backend container
docker compose exec backend alembic upgrade head
# Seed admin
docker compose exec backend python -m app.cli.seed admin admin
# Verify
curl -sX POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin"}'
```

Expected: JSON containing `access_token`.

Open `http://localhost:3000/login` in a browser, log in as `admin`/`admin`, see the devices page render with seeded devices.

- [ ] **Step 4: Commit**

```bash
git add backend/Dockerfile frontend/Dockerfile
git commit -m "feat(deploy): docker-compose images for backend and frontend"
```

---

## Self-Review Summary

- **Spec coverage**:
  - §1 Architecture → Task 16 (main.py lifespan), Task 12 (scheduler)
  - §1.5 Port mapping → CrossTestProtocol abstraction (Task 6) ready to wire when real protocol lands
  - §2 Data model → Tasks 2, 3
  - §3.2 Health-check → Tasks 5, 7, 8, plus periodic job in Task 16
  - §3.3 Cross-test scheduler → Tasks 9–14
  - §3.4 Device lock semantics → Task 9 + Task 14 invariant test
  - §3.6 Frontend polling → Tasks 19–23
  - §4.1 Failure modes → handled in Task 12 (worker except), Task 16 (recover_state), Task 17 (cancel endpoint)
  - §4.2 .env knobs → Task 0 (.env.example), Task 1 (Settings)
  - §4.4 Tests → unit + integration across Tasks 4–14
  - §5 TBD protocol → encapsulated in `crosstest_proto.py` (Task 6); only Task 6 changes when finalized
- **Placeholders**: only `StubCrossTestProtocol` (intentional and called out in Task 6 docstring and spec §5).
- **Type consistency**: `pick_next_dispatchable`, `try_acquire_pair`, `release_pair`, `WorkItem`, `PairResult`, `CrossTestProtocol.run_pair` names are consistent across Tasks 6, 9, 11, 12.
