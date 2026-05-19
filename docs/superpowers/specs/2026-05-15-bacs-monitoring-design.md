# BACS 모니터링 & Cross-Test 시스템 — 설계서

- **작성일**: 2026-05-15
- **상태**: Draft (사용자 검토 대기)
- **관련 문서**: `BACS_Control.md` (프로토콜 명세)

---

## 1. 시스템 개요 & 아키텍처

### 1.1 목적

전국에 분산된 약 300대의 BACS 장비에 대해 다음 두 가지 기능을 제공한다.

1. **Health-check**: UDP Heartbeat 기반 상태 모니터링 (주기 + 수동)
2. **Cross-test**: 사용자가 선택한 N개 장비 간 N×(N-1) 쌍의 송수신 검증

### 1.2 기술 스택

- Frontend: Next.js (App Router)
- Backend: FastAPI (Python, asyncio)
- DB: MySQL (SQLAlchemy async, Alembic)
- 스케줄러: APScheduler (health-check 주기 잡)
- 배포: docker-compose (사내망)

### 1.3 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│  Next.js (Frontend)                                          │
│  - 로그인 / BACS 목록 / Health 상태 / Cross-test 매트릭스    │
│  - 3초 주기 polling으로 상태 갱신                            │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST (JSON)
┌──────────────────────────┴──────────────────────────────────┐
│  FastAPI (단일 프로세스, asyncio)                            │
│  ├─ API Layer        : 인증, BACS 조회, 테스트 제어         │
│  ├─ HealthCheck Svc  : APScheduler 1분 주기 UDP Heartbeat   │
│  ├─ CrossTest Svc    : asyncio 큐 + 장비 락 + 워커 풀       │
│  ├─ BACS Protocol    : UDP/TCP 메시지 빌더·파서 (일부 TBD)  │
│  └─ Repository       : SQLAlchemy async, MySQL              │
└──────────────────────────┬──────────────────────────────────┘
                           │ UDP/TCP :7788
                  ┌────────┴────────┐
                  │   BACS × 300    │
                  └─────────────────┘
```

### 1.4 핵심 설계 원칙

- BACS 프로토콜 계층은 인터페이스(`CrossTestProtocol`)로 추상화. BACS↔BACS 호출시험 메커니즘은 추후 명세될 예정이며, 구현체 교체만으로 본 설계의 다른 부분은 변경 없이 동작한다.
- 비즈니스 로직(스케줄러/락) 은 프로토콜과 독립적으로 단위 테스트 가능.
- 모든 외부 I/O 는 async. 워커 동시성은 명시적 세마포어와 장비 락으로 제한.
- 단일 FastAPI 프로세스(asyncio) 모델. Celery/Redis 등 분산 큐 미도입 (사내망 300대 규모에는 과한 복잡도).

### 1.5 핵심 제약 사항

- **장비당 동시 1세션**: BACS 한 대는 동시에 하나의 cross-test 쌍에만 참여할 수 있다. 이 제약이 스케줄링의 핵심 결정 요인이다.
- **포트 페어링**: TX 0 → RX 2, TX 1 → RX 3 의 두 고정 페어로 단방향 1회 테스트가 구성된다. (양방향 검증은 src/dst 를 교대하는 두 쌍으로 표현)
- **세션당 소요 시간**: 성공 약 30초, 실패 약 60초 (timeout 70초 설정)

---

## 2. 데이터 모델 (MySQL)

```sql
-- 사용자 (간단 로그인)
users
  id            BIGINT PK
  username      VARCHAR(64) UNIQUE
  password_hash VARCHAR(255)
  created_at    DATETIME

-- BACS 장비 마스터 (DB 직접 관리, UI 조회 전용)
bacs_devices
  id           BIGINT PK
  name         VARCHAR(128)
  node_id      SMALLINT          -- 0~63
  ip_address   VARCHAR(45)
  udp_port     INT DEFAULT 7788
  tcp_port     INT DEFAULT 7788
  location     VARCHAR(255)
  enabled      BOOLEAN DEFAULT TRUE
  created_at   DATETIME
  updated_at   DATETIME
  UNIQUE(ip_address, udp_port)

-- 장비별 최신 health 상태 (1행/장비, 이력 미보관)
device_health
  bacs_id          BIGINT PK FK→bacs_devices.id
  status           ENUM('ok','fail','unknown')
  last_checked_at  DATETIME
  last_ok_at       DATETIME NULL
  last_error       VARCHAR(255) NULL
  consecutive_fail INT DEFAULT 0

-- 테스트 세션 (사용자가 "테스트 시작"을 누른 단위)
test_sessions
  id           BIGINT PK
  user_id      BIGINT FK→users.id
  status       ENUM('queued','running','completed','cancelled','failed')
  device_ids   JSON
  total_pairs  INT               -- N*(N-1)
  done_pairs   INT DEFAULT 0
  ok_pairs     INT DEFAULT 0
  fail_pairs   INT DEFAULT 0
  started_at   DATETIME
  finished_at  DATETIME NULL
  INDEX(user_id, started_at DESC)

-- 세션 내 개별 쌍(src→dst) 진행 상태
test_session_pairs
  id            BIGINT PK
  session_id    BIGINT FK→test_sessions.id
  src_bacs_id   BIGINT FK→bacs_devices.id
  dst_bacs_id   BIGINT FK→bacs_devices.id
  status        ENUM('pending','running','ok','fail','skipped')
  started_at    DATETIME NULL
  finished_at   DATETIME NULL
  error_message VARCHAR(255) NULL
  INDEX(session_id, status)
  INDEX(src_bacs_id), INDEX(dst_bacs_id)

-- 장비 쌍별 최신 cross-test 결과 (매트릭스 뷰 단일 진실 소스)
pair_latest_result
  src_bacs_id   BIGINT FK→bacs_devices.id
  dst_bacs_id   BIGINT FK→bacs_devices.id
  status        ENUM('ok','fail')
  tested_at     DATETIME
  session_id    BIGINT FK→test_sessions.id
  error_message VARCHAR(255) NULL
  PRIMARY KEY(src_bacs_id, dst_bacs_id)

-- 진행중 장비 점유 (인메모리 락의 영속 백업)
device_locks
  bacs_id     BIGINT PK FK→bacs_devices.id
  session_id  BIGINT FK→test_sessions.id
  acquired_at DATETIME
```

### 2.1 설계 메모

- `pair_latest_result` 는 매트릭스 UI의 단일 진실 소스. 세션 워커가 쌍을 완료할 때마다 UPSERT.
- `device_locks` 테이블은 프로세스 재시작 시 stale lock 정리용. 실제 락 획득은 인메모리 `asyncio.Lock` (성능).
- `test_session_pairs` 는 세션 생성 시 N×(N-1)개를 미리 INSERT. 300대 풀스캔 시 약 89,700 row — MySQL 부담 없음.
- "쌍"의 의미: src→dst 단방향 1건 = 1 row. A↔B 양방향 검증은 2 row.

---

## 3. 컴포넌트 & 데이터 흐름

### 3.1 백엔드 모듈 구성

```
backend/
├─ main.py                  # FastAPI 앱, lifespan(스케줄러 시작/종료, stale lock 정리)
├─ api/
│  ├─ auth.py               # POST /auth/login, /auth/logout
│  ├─ devices.py            # GET /devices, GET /devices/{id}/health
│  ├─ health.py             # POST /health/refresh
│  └─ tests.py              # POST /tests, GET /tests/{id}, GET /tests/{id}/pairs,
│                           # POST /tests/{id}/cancel, GET /pair-matrix
├─ services/
│  ├─ health_service.py     # 주기 health-check 잡, 단일 BACS Heartbeat
│  ├─ crosstest/
│  │  ├─ scheduler.py       # 세션 큐, 워커 풀, pair 디스패치
│  │  ├─ device_locker.py   # asyncio.Lock per BACS + device_locks 백업
│  │  └─ runner.py          # 단일 (src,dst) 쌍 실행 (protocol 호출)
│  └─ session_service.py    # 세션 생성/취소/상태 집계
├─ protocol/
│  ├─ udp_client.py         # UDP Heartbeat (SE_MA_Connect_REQ / RPT)
│  ├─ tcp_client.py         # TCP 제어 세션 (Connect_Level_RPT, Start_Up_RPT)
│  ├─ messages.py           # struct pack/unpack, Type/MsgType 상수
│  └─ crosstest_proto.py    # ★ BACS↔BACS 호출시험 (TBD - 추후 확정)
├─ repositories/            # SQLAlchemy async repository
├─ models/                  # SQLAlchemy ORM
└─ schemas/                 # Pydantic request/response
```

### 3.2 핵심 인터페이스 (TBD 캡슐화)

```python
class CrossTestProtocol(Protocol):
    async def run_pair(
        self, src: BacsDevice, dst: BacsDevice, timeout: float
    ) -> PairResult:
        """src→dst 단방향 테스트 1건. 성공 시 ~30s, 실패 시 ~60s."""
```

실제 BACS↔BACS 메커니즘이 확정되면 이 인터페이스 구현체(`crosstest_proto.py`)만 채우면 된다. 스케줄러/락/DB는 변경 불필요.

### 3.3 Health-check 흐름

```
APScheduler (1분 주기, .env: HEALTH_CHECK_INTERVAL_SEC)
   │
   ▼
HealthCheckService.run_all()
   │  asyncio.gather(check_one(b) for b in enabled_devices)
   │  Semaphore(HEALTH_CHECK_CONCURRENCY) 로 동시성 제한
   ▼
for each BACS:
   send UDP SE_MA_Connect_REQ → :7788
   recv MA_SE_Connect_RPT (3s timeout)
   UPSERT device_health
```

- 수동 재시도: `POST /health/refresh` → 동일 로직 즉시 1회 실행
- 결과는 `device_health` 1행으로 덮어씀 (이력 미보관)

### 3.4 Cross-test 흐름

```
사용자: POST /tests {device_ids: [...]}
   │
   ▼
SessionService.create():
   1) Validate device_ids
   2) INSERT test_sessions(status='queued')
   3) INSERT N*(N-1) test_session_pairs(status='pending')
   4) Enqueue to CrossTestScheduler
   5) Return session_id
   │
   ▼
CrossTestScheduler (백그라운드 asyncio task, 영구 실행)
   │
   └─ 디스패치 루프:
        while session has pending pairs:
            pair = pick_next_dispatchable(pending_pairs)
              # src/dst 모두 락 획득 가능한 쌍을 찾음
              # 전체 세션 + 다른 세션과 장비 충돌 없는 쌍 우선
            if pair is None:
                await wait_for_lock_release_event()
                continue
            if not acquire(pair.src) or not acquire(pair.dst):
                release_partial(); continue
            asyncio.create_task(worker(pair))
            # Semaphore(CROSSTEST_MAX_CONCURRENT_PAIRS) 로 추가 제한
```

**Worker 실행**

```
worker(pair):
   try:
      UPDATE test_session_pairs SET status='running', started_at=NOW()
      result = await crosstest_proto.run_pair(src, dst, timeout=70s)
      UPDATE test_session_pairs SET status='ok'|'fail', finished_at, error_message
      UPSERT pair_latest_result
      INCR session.done_pairs, ok_pairs|fail_pairs
   finally:
      release_lock(src); release_lock(dst)
      notify_lock_release_event()
   if session.done_pairs == total_pairs:
      UPDATE test_sessions SET status='completed', finished_at=NOW()
```

### 3.5 장비 락 의미

- 한 BACS는 동시 1세션만 참여 가능 → 모든 활성 cross-test 세션을 통틀어 전역 락
- 사용자 A의 [BACS1~15]와 사용자 B의 [BACS16~30]은 락 충돌 없어 병렬 실행
- 사용자 B의 [BACS10~20]은 겹치는 BACS가 풀릴 때까지 자동 대기

### 3.6 Frontend Polling

```
페이지 진입
  ├─ GET /devices + /devices/health  → 장비 + health 상태 목록 렌더
  └─ setInterval(3s):
       if active session_id:
          GET /tests/{id}  → progress bar, done/ok/fail
          GET /tests/{id}/pairs?status=running → "지금 테스트 중" 표시
       else:
          GET /devices/health
```

매트릭스 뷰: `GET /pair-matrix?device_ids=...` → 선택 장비 간 latest result 격자.

---

## 4. 에러 처리 & 운영

### 4.1 실패 분류와 처리

| 실패 유형 | 위치 | 처리 방식 |
|---|---|---|
| UDP Heartbeat timeout | health-check | `device_health.status='fail'`, `consecutive_fail++` |
| UDP 응답 형식 오류 | health-check | `status='fail'`, `last_error`에 파싱 에러 기록 |
| Cross-test pair timeout | worker | `test_session_pairs.status='fail'`, 다음 쌍 계속 진행 |
| Cross-test 예외(소켓/파싱) | worker | 위와 동일. 세션 전체는 계속 |
| health-check fail 장비를 cross-test 시작 | API | 경고 반환하되 진행 허용 |
| 사용자 cancel | API | `session.status='cancelled'`. 진행 중 워커는 완료까지 두고 신규 dispatch 중단 |
| FastAPI 재시작 | lifespan startup | `device_locks` 전체 삭제, `status IN ('queued','running')` 세션을 `failed` 처리 |
| MySQL 일시 단절 | repository | 재시도 3회, 그래도 실패면 해당 작업 실패. 다음 사이클에 정상화 |

### 4.2 동시성 한계 (.env)

```
HEALTH_CHECK_INTERVAL_SEC = 60
HEALTH_CHECK_TIMEOUT_SEC = 3
HEALTH_CHECK_CONCURRENCY = 50
CROSSTEST_PAIR_TIMEOUT_SEC = 70
CROSSTEST_MAX_CONCURRENT_PAIRS = 150
CROSSTEST_DISPATCH_INTERVAL_MS = 100
```

### 4.3 로깅 / 관측

- 구조화 로그(JSON)
- 핵심 이벤트: `health_check.tick`, `crosstest.session.created/completed`, `crosstest.pair.start/ok/fail`, `lock.acquire/release/wait`
- `GET /healthz` (앱 상태), `GET /metrics` (선택)

### 4.4 테스트 전략

**유닛 (pytest + pytest-asyncio)**
- `DeviceLocker`: 동시 락 획득/해제, 데드락 방지, 부분 락 롤백
- `CrossTestScheduler.pick_next_dispatchable`: 다양한 락 상태에서 올바른 쌍 선택
- `protocol.messages` pack/unpack 라운드트립 (BACS_Control.md 예시 바이트 검증)
- Pydantic 스키마, 인증 미들웨어

**통합**
- 가짜 BACS 시뮬레이터(asyncio UDP/TCP echo server) 로 송수신 검증
- 시나리오: 300대 모의 장비, 15대 선택 → 모든 쌍 완료, 카운터 일치
- 사용자 A/B 의 겹치는 장비 세트 동시 실행 → 락 대기와 순서 보장

**E2E (선택, Playwright)**
- 로그인 → 장비 목록 → 테스트 시작 → 진행률 polling → 완료
- 매트릭스 뷰 렌더

**부하**
- 시뮬레이터 300대 × 풀스캔(89,700 쌍) → 종료 시간/메모리/DB 부하 측정
- 목표: 메모리 < 500MB, MySQL CPU 안정

### 4.5 보안 / 운영

- 로그인: bcrypt + JWT (HttpOnly cookie)
- 사내망 가정 — HTTPS는 리버스 프록시(nginx)
- BACS IP 사내 NW 한정, 외부 호출 없음
- 마이그레이션: Alembic
- 배포: docker-compose (FastAPI / Next.js / MySQL)

---

## 5. 알려진 TBD 항목

- **BACS↔BACS 호출시험 메커니즘**: 송수신 측에서 어떤 메시지를 주고받고, 성공/실패를 어떻게 판정하는지의 상세 프로토콜. `CrossTestProtocol` 인터페이스 뒤에 캡슐화되어 있어 본 설계의 다른 부분에 영향 없이 추후 구현 가능.
