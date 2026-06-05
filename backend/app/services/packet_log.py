"""
세션별 패킷 이벤트 허브 (인메모리 pub/sub + 히스토리 버퍼).

호출시험 중 BACS TCP 세션에서 오가는 패킷을 실시간 및 늦게 연결된
SSE 클라이언트에도 전달하기 위해 히스토리 버퍼를 함께 유지한다.

설계:
  - 세션 ID별로 asyncio.Queue(실시간) + list(히스토리) 를 유지한다.
  - crosstest_proto 가 패킷 송수신 시마다 publish() 를 호출한다.
  - SSE 엔드포인트가 subscribe() 로 (히스토리, 큐)를 꺼내 스트리밍한다.
    늦게 연결된 클라이언트도 히스토리를 먼저 받고 이후 실시간 이벤트를 수신한다.
  - 세션이 종료되면 schedule_cleanup() 으로 5분 후 메모리를 해제한다.
    (SSE 클라이언트가 늦게 연결해도 히스토리를 전달할 수 있도록 유예 시간 부여)
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

# 세션 당 히스토리 최대 보관 이벤트 수
_MAX_HISTORY = 1000
# 세션 완료 후 메모리 해제까지 유예 시간 (초)
_CLEANUP_DELAY_SEC = 300


@dataclass
class PacketEvent:
    """단일 패킷 이벤트 — TX(송신) 또는 RX(수신) 방향 모두 사용."""

    session_id: int
    # 페어 라벨 (예: "192.168.1.10:Port0 → 192.168.1.11:Port2")
    pair_label: str
    # TX = 서버→BACS 송신, RX = BACS→서버 수신
    direction: str
    # 프로토콜 단계 레이블 (예: "CONNECT_REQ", "STARTUP_RPT", "CALL_REQ[Port=0]" …)
    step: str
    # raw 바이트를 공백 구분 hex 문자열로 표현 (예: "01 10 09 00 ...")
    hex_dump: str
    # 명세서 기준으로 파싱한 필드 딕셔너리 (UI 테이블 용)
    parsed: dict[str, Any]
    # ISO 8601 UTC 타임스탬프
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


# ─── 세션별 상태 ───────────────────────────────────────────────────────────

# 세션 ID → 실시간 큐 (SSE 리스너가 소비)
_session_queues: dict[int, asyncio.Queue[PacketEvent | None]] = {}
# 세션 ID → 히스토리 (늦게 연결된 SSE에 재생용)
_session_history: dict[int, list[PacketEvent]] = {}
# 세션 ID → 완료 여부 (히스토리 재생 완료 후 즉시 done 보내기 위해)
_session_done: dict[int, bool] = {}


def _ensure_session(session_id: int) -> None:
    """세션 상태를 초기화한다 (이미 있으면 아무것도 안 함)."""
    if session_id not in _session_queues:
        _session_queues[session_id] = asyncio.Queue(maxsize=_MAX_HISTORY * 2)
        _session_history[session_id] = []
        _session_done[session_id] = False


def publish(session_id: int, event: PacketEvent) -> None:
    """패킷 이벤트를 해당 세션의 큐와 히스토리에 동시에 저장한다.

    큐가 가득 차면 가장 오래된 이벤트를 버리고 새 이벤트를 삽입한다.
    히스토리는 _MAX_HISTORY 개까지만 보관한다.
    """
    _ensure_session(session_id)
    # 히스토리 저장
    hist = _session_history[session_id]
    if len(hist) < _MAX_HISTORY:
        hist.append(event)
    # 실시간 큐에 투입
    q = _session_queues[session_id]
    if q.full():
        try:
            q.get_nowait()
        except asyncio.QueueEmpty:
            pass
    q.put_nowait(event)


def publish_done(session_id: int) -> None:
    """세션 종료 신호를 큐에 투입한다. SSE 제너레이터가 이를 보고 스트림을 닫는다."""
    _ensure_session(session_id)
    _session_done[session_id] = True
    q = _session_queues[session_id]
    try:
        q.put_nowait(None)          # type: ignore[arg-type]
    except asyncio.QueueFull:
        pass


def get_history(session_id: int) -> list[PacketEvent]:
    """세션의 히스토리 이벤트 목록을 반환한다 (복사본)."""
    return list(_session_history.get(session_id, []))


def is_done(session_id: int) -> bool:
    """세션이 이미 완료된 상태인지 반환한다."""
    return _session_done.get(session_id, False)


async def subscribe(session_id: int) -> "asyncio.Queue[PacketEvent | None]":
    """세션의 실시간 큐를 반환한다 (없으면 자동 생성)."""
    _ensure_session(session_id)
    return _session_queues[session_id]


def cleanup(session_id: int) -> None:
    """세션 관련 메모리를 즉시 해제한다."""
    _session_queues.pop(session_id, None)
    _session_history.pop(session_id, None)
    _session_done.pop(session_id, None)


def schedule_cleanup(session_id: int, delay: float = _CLEANUP_DELAY_SEC) -> None:
    """세션 종료 후 delay초 뒤에 메모리를 해제하도록 비동기 타이머를 등록한다.

    SSE 클라이언트가 늦게 연결해도 히스토리를 전달할 수 있도록
    즉시 삭제하지 않고 유예 시간을 둔다.
    """
    async def _deferred():
        await asyncio.sleep(delay)
        cleanup(session_id)

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_deferred())
    except RuntimeError:
        # 이벤트 루프가 없는 문맥(테스트 등)에서는 즉시 정리
        cleanup(session_id)
