# Windows Portable 패키지 전략

## 개요

NCVS UDP Test 프로젝트를 **Docker 없이, 인터넷 없이** Windows PC에서 실행 가능한
단독 실행 패키지로 만드는 전략 문서다.

### 핵심 원칙

> **서버(운영)와 로컬(테스트)의 DB가 다르다.**
> 코드는 단 하나다. `.env` 파일 하나만 바꿔서 드라이버를 분기한다.

| 환경 | DB | 드라이버 | 실행 방식 |
|---|---|---|---|
| **실서버 (운영)** | MySQL 8.0 | `aiomysql` | Docker Compose |
| **로컬 PC (테스트)** | SQLite (파일) | `aiosqlite` | Windows Portable |

SQLAlchemy/Alembic은 `DATABASE_URL` 값만 보고 드라이버를 자동 선택하므로
**비즈니스 로직 코드는 한 줄도 바꾸지 않는다.**

---

## 1. 최종 패키지 구조

```
ncvs-package/                    ← USB 또는 파일 전달 단위
│
├── start.bat                    ← ★ 메인 런처 (더블클릭 실행)
├── stop.bat                     ← 서버 종료
├── install.bat                  ← 최초 1회만 실행 (DB 초기화 + 계정 생성)
├── README.txt                   ← 사용자 안내문 (한국어)
│
├── python/                      ← Python 3.12 embeddable (설치 불필요)
│   ├── python.exe
│   ├── python312.zip
│   └── Lib/
│       └── site-packages/       ← 모든 pip 패키지 (wheel 형태로 사전 설치)
│           ├── fastapi/
│           ├── uvicorn/
│           ├── sqlalchemy/
│           ├── aiosqlite/       ← SQLite 비동기 드라이버 (로컬 전용)
│           ├── alembic/
│           └── ...
│
├── node/                        ← Node.js 20 LTS portable (설치 불필요)
│   └── node.exe
│
├── backend/                     ← FastAPI 백엔드 소스
│   ├── app/
│   ├── alembic/
│   ├── alembic.ini
│   └── .env                     ← 로컬용 환경변수 (SQLite URL 사용)
│
├── frontend/                    ← Next.js standalone 빌드 결과물
│   ├── server.js                ← Next.js standalone 진입점
│   ├── .next/
│   └── public/
│
└── data/
    └── ncvs.db                  ← SQLite DB 파일 (install.bat 실행 시 자동 생성)
```

### 예상 패키지 크기

| 구성 요소 | 크기 |
|---|---|
| Python 3.12 embeddable | ~12 MB |
| pip 패키지 wheel 전체 | ~120 MB |
| Node.js 20 portable | ~35 MB |
| Next.js standalone 빌드 | ~50 MB |
| 백엔드 소스 | ~2 MB |
| **합계** | **~220 MB** |

---

## 2. DB 분기 전략 상세

### 2-1. `.env` 파일 분기

```
프로젝트 루트/
├── .env                ← 서버(운영)용 — MySQL, Docker Compose가 읽음
├── .env.example        ← 두 환경 모두 예시 포함
└── backend/
    └── .env            ← 로컬(테스트)용 — SQLite, Portable 패키지가 읽음
```

**서버 `.env` (운영, 변경 없음)**
```env
DATABASE_URL=mysql+aiomysql://ncvs:ncvs@mysql:3306/ncvs
JWT_SECRET=change-me-in-production
...
```

**`backend/.env` (로컬 테스트용, 신규 생성)**
```env
# ★ 로컬 테스트 전용 — SQLite 파일 DB
DATABASE_URL=sqlite+aiosqlite:///./data/ncvs.db
JWT_SECRET=local-test-secret-key-32chars-min
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

HEALTH_CHECK_INTERVAL_SEC=30
HEALTH_CHECK_TIMEOUT_SEC=3
HEALTH_CHECK_CONCURRENCY=50

CROSSTEST_PAIR_TIMEOUT_SEC=70
CROSSTEST_MAX_CONCURRENT_PAIRS=150
CROSSTEST_DISPATCH_INTERVAL_MS=100
```

### 2-2. SQLite 관련 코드 변경 사항

| 파일 | 변경 내용 |
|---|---|
| `backend/pyproject.toml` | `aiosqlite>=0.20` 의존성 추가 |
| `frontend/next.config.mjs` | `output: 'standalone'` 추가 |
| `backend/app/db.py` | SQLite는 `check_same_thread=False` 옵션 필요 — connect_args 분기 추가 |

**`app/db.py` SQLite 호환 처리 예시**
```python
from app.config import settings

# SQLite는 connect_args 필요, MySQL은 불필요
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_async_engine(settings.DATABASE_URL, connect_args=connect_args)
```

> Alembic `env.py`도 동일하게 분기 처리 필요.

---

## 3. 빌드 프로세스 (macOS 개발 머신에서 실행)

빌드는 **개발 머신(macOS)** 에서 수행하며, 결과물을 Windows PC에 전달한다.

### 3-1. 빌드 스크립트 `build-windows-package.sh`

```
scripts/
└── build-windows-package.sh
```

**단계별 흐름:**

```
[Step 1] Next.js standalone 빌드
  cd frontend && npm run build
  → frontend/.next/standalone/ 생성

[Step 2] Python 3.12 Windows embeddable 다운로드
  curl -O https://www.python.org/ftp/python/3.12.x/python-3.12.x-embed-amd64.zip
  → 인터넷 가능한 개발 머신에서 1회만 수행

[Step 3] Windows용 pip wheel 사전 다운로드
  pip download --platform win_amd64 --python-version 312 \
    --only-binary :all: \
    -r requirements-windows.txt \
    -d ./wheels/
  → macOS에서 Windows 바이너리 wheel을 미리 내려받음

[Step 4] Python embeddable에 패키지 설치
  Python embeddable은 pip가 없음 → get-pip.py로 설치 후 wheel 일괄 설치

[Step 5] Node.js 20 LTS Windows portable 다운로드
  curl -O https://nodejs.org/dist/v20.x.x/node-v20.x.x-win-x64.zip

[Step 6] 런처 .bat 파일 생성

[Step 7] 전체 패키지 zip 압축
  → ncvs-package-YYYYMMDD.zip
```

### 3-2. `requirements-windows.txt`

서버 의존성에서 `aiomysql` 제거, `aiosqlite` 추가한 별도 파일.

```
fastapi>=0.110
uvicorn[standard]>=0.27
sqlalchemy[asyncio]>=2.0
aiosqlite>=0.20           ← 로컬 SQLite용 (MySQL 대체)
alembic>=1.13
pydantic>=2.6
pydantic-settings>=2.2
apscheduler>=3.10
bcrypt>=4.0
cryptography>=42.0
pyjwt>=2.8
loguru>=0.7
```

> `aiomysql`, `pymysql`은 제외한다. 로컬 PC에서는 MySQL을 쓰지 않는다.

---

## 4. 런처 스크립트

### 4-1. `install.bat` (최초 1회)

```batch
@echo off
chcp 65001 > nul
echo [NCVS] 초기 설치를 시작합니다...

:: DB 디렉토리 생성
if not exist "data" mkdir data

:: Alembic 마이그레이션 (SQLite DB 파일 + 테이블 생성)
cd backend
..\python\python.exe -m alembic upgrade head
if errorlevel 1 (
    echo [ERROR] DB 초기화 실패
    pause
    exit /b 1
)

:: 관리자 계정 시드 (admin/admin)
..\python\python.exe -m app.cli.seed admin admin
echo [NCVS] 초기 설치 완료.
echo [INFO] 기본 계정: admin / admin
pause
```

### 4-2. `start.bat` (매번 실행)

```batch
@echo off
chcp 65001 > nul
echo [NCVS] 서버를 시작합니다...

:: 백엔드 백그라운드 실행
cd backend
start "NCVS Backend" ..\python\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
cd ..

:: 잠시 대기 후 프론트엔드 실행
timeout /t 3 /nobreak > nul
cd frontend
start "NCVS Frontend" ..\node\node.exe server.js
cd ..

:: 브라우저 오픈
timeout /t 3 /nobreak > nul
start http://localhost:3000

echo [NCVS] 실행 중
echo   UI:  http://localhost:3000
echo   API: http://localhost:8000/docs
echo 종료하려면 stop.bat 을 실행하세요.
```

### 4-3. `stop.bat`

```batch
@echo off
echo [NCVS] 서버를 종료합니다...
taskkill /FI "WINDOWTITLE eq NCVS Backend*" /F > nul 2>&1
taskkill /FI "WINDOWTITLE eq NCVS Frontend*" /F > nul 2>&1
echo [NCVS] 종료 완료.
```

---

## 5. Alembic SQLite 호환 설정

SQLite는 컬럼 타입, ALTER TABLE 지원이 MySQL과 다르다.
`alembic/env.py`에 렌더링 옵션을 추가한다.

```python
# alembic/env.py 에 추가
from sqlalchemy import engine_from_config
from app.config import settings

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        # SQLite: BATCH 모드 사용 (ALTER TABLE 에뮬레이션)
        render_as_batch=settings.DATABASE_URL.startswith("sqlite"),
    )
    ...
```

> `render_as_batch=True` 없으면 SQLite에서 기존 컬럼 변경 마이그레이션이 실패한다.

---

## 6. Windows PC에서 실행 순서

```
1. ncvs-package-YYYYMMDD.zip 수신
2. 압축 해제 (예: C:\ncvs-package\)
3. install.bat  ← 최초 1회만 더블클릭
4. start.bat    ← 더블클릭
5. 브라우저에서 http://localhost:3000 접속
6. 로그인: admin / admin
7. 장비 등록 → 헬스체크 → 호출시험 확인
```

---

## 7. 구현 순서 (태스크)

| 순서 | 작업 | 파일 |
|---|---|---|
| 1 | `aiosqlite` 의존성 추가 | `backend/pyproject.toml` |
| 2 | SQLite connect_args 분기 | `backend/app/db.py` |
| 3 | Alembic render_as_batch 분기 | `backend/alembic/env.py` |
| 4 | Next.js standalone 모드 활성화 | `frontend/next.config.mjs` |
| 5 | 로컬용 `.env` 파일 생성 | `backend/.env.local` |
| 6 | Windows requirements 파일 생성 | `scripts/requirements-windows.txt` |
| 7 | 빌드 스크립트 작성 | `scripts/build-windows-package.sh` |
| 8 | 런처 배치 파일 작성 | `scripts/windows/` |
| 9 | 로컬 SQLite 환경에서 동작 검증 | — |
| 10 | Windows 패키지 빌드 및 압축 | — |

---

## 8. 주의사항 및 제약

| 항목 | 내용 |
|---|---|
| **포트 충돌** | 3000, 8000 포트가 이미 사용 중이면 실행 실패. `start.bat`에 사전 점검 로직 추가 예정 |
| **Windows 경로** | Python embeddable은 `./` 상대경로가 `\` 백슬래시. SQLite URL은 `/` 슬래시 유지 필요 |
| **SQLite 동시성** | SQLite는 write lock이 전역. 대량 동시 호출시험 시 성능 저하 가능. 테스트 목적이므로 허용 범위 |
| **데이터 초기화** | `data/ncvs.db` 파일 삭제 후 `install.bat` 재실행으로 초기화 가능 |
| **방화벽** | Windows 방화벽이 3000/8000 포트를 차단할 수 있음. `install.bat`에서 자동 허용 규칙 추가 |
| **운영 DB 영향 없음** | 로컬 SQLite는 완전히 독립 파일. 서버 MySQL에 어떤 영향도 없음 |

---

## 9. 서버(운영) 배포 시 변경사항 없음

로컬 포터블 작업으로 인한 **서버 배포 변경사항 없음.**

| 항목 | 서버 운영 영향 |
|---|---|
| `pyproject.toml` `aiosqlite` 추가 | 없음 (설치되어도 사용 안 함) |
| `db.py` connect_args 분기 | 없음 (MySQL URL이면 빈 dict 반환) |
| `alembic/env.py` render_as_batch | 없음 (MySQL URL이면 False) |
| `next.config.mjs` standalone | 없음 (Docker 빌드 결과는 동일) |
| 로컬 `backend/.env` | 없음 (Docker Compose는 루트 `.env` 사용) |
