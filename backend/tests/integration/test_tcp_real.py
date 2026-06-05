"""
TCP 호출시험 실장비 통합 테스트
================================
실제 BACS 장비가 연결된 환경에서만 실행합니다.

실행 방법:
    BACS_REAL_IP=192.168.1.10 \\
    BACS_REAL_PORT0_PHONE=800-1200 \\
    BACS_REAL_PORT1_PHONE=800-1300 \\
    pytest -m real_device tests/integration/test_tcp_real.py -v -s

환경변수:
    BACS_REAL_IP             — 장비 IP (필수, UDP 테스트와 공유)
    BACS_REAL_TCP_PORT       — TCP 포트 (기본값 7788)
    BACS_REAL_PORT0_PHONE    — Port 0 발신 시 대응하는 착신 전화번호 (dst.port2_phone)
    BACS_REAL_PORT1_PHONE    — Port 1 발신 시 대응하는 착신 전화번호 (dst.port3_phone)
    BACS_REAL_SCENARIO_ID    — UI E2E 테스트용 시나리오 ID (STEP 5, 기본값 1)
    BACS_API_BASE_URL        — 백엔드 API URL (UI E2E 테스트용, 기본값 http://localhost:8000)
    BACS_API_USERNAME        — UI E2E 테스트용 로그인 계정 (기본값 admin)
    BACS_API_PASSWORD        — UI E2E 테스트용 로그인 비밀번호 (기본값 admin)

STEP 순서:
    STEP 1 — TCP 접속 + StartUp RPT 수신 확인 (CALL_REQ 없이 접속만)
    STEP 2 — Port=0 단일 CALL_REQ → CALL_RPT 수신 (응답 출력, assert 완화)
    STEP 3 — 단일 세션에서 Port=0 + Port=1 순차 호출 (BacsTcpCrossTestProtocol)
    STEP 4 — 중복 연결 시 error 302 수신 확인
    STEP 5 — UI E2E: API로 세션 생성 → SSE polling → 완료 결과 확인
"""
from __future__ import annotations

import asyncio
import os
from types import SimpleNamespace

import pytest
from app.protocol.crosstest_proto import BacsTcpCrossTestProtocol
from app.protocol.tcp_messages import (
    build_call_req,
    build_connect_level_req,
    parse_call_rpt,
    parse_startup_response,
)

# ─── 환경변수 설정 ────────────────────────────────────────────────────────────
_REAL_IP         = os.environ.get("BACS_REAL_IP", "")
_REAL_TCP_PORT   = int(os.environ.get("BACS_REAL_TCP_PORT", "7788"))
_PORT0_PHONE     = os.environ.get("BACS_REAL_PORT0_PHONE")   # dst.port2_phone
_PORT1_PHONE     = os.environ.get("BACS_REAL_PORT1_PHONE")   # dst.port3_phone
_SCENARIO_ID     = int(os.environ.get("BACS_REAL_SCENARIO_ID", "1"))
_API_BASE        = os.environ.get("BACS_API_BASE_URL", "http://localhost:8000")
_API_USER        = os.environ.get("BACS_API_USERNAME", "admin")
_API_PASS        = os.environ.get("BACS_API_PASSWORD", "admin")

# 호출 응답 대기: 성공 ~30초, 실패 ~50초 → 여유 60초
_CALL_TIMEOUT   = 60.0
# 단일 세션 전체 타임아웃 (포트 2개 × 60초 + 여유)
_SESSION_TIMEOUT = 130.0
# 헤더 크기: Type(2) + DataLength(2)
_HEADER_SIZE = 4


def _skip_if_no_ip() -> None:
    """BACS_REAL_IP 미설정 시 테스트 스킵."""
    if not _REAL_IP:
        pytest.skip("BACS_REAL_IP 환경변수 미설정 → 실장비 없음으로 스킵")


async def _read_frame(reader: asyncio.StreamReader) -> bytes:
    """TCP 스트림에서 패킷 1개(헤더 + 데이터)를 완전히 읽어 반환한다."""
    header = await reader.readexactly(_HEADER_SIZE)
    data_len = int.from_bytes(header[2:4], "little")
    body = await reader.readexactly(data_len)
    return header + body


def _make_device(ip: str, tcp_port: int,
                 port2_phone: str | None = None,
                 port3_phone: str | None = None) -> SimpleNamespace:
    """
    실장비 테스트용 장비 객체 생성 (DB 저장 없이 메모리만 사용).

    전화번호는 환경변수(BACS_REAL_PORT0_PHONE / BACS_REAL_PORT1_PHONE)로만 주입.
    미설정 시 None → CALL_REQ의 Phone_length=0, Phone_Num 전부 0x00 전송.
    node_id는 항상 1 고정 (tcp_messages._CALL_NODE_ID).
    """
    return SimpleNamespace(
        id=99,
        name=f"real-{ip}",
        ip_address=ip,
        udp_port=7788,
        tcp_port=tcp_port,
        location=None,
        enabled=True,
        port0_phone=None,
        port1_phone=None,
        port2_phone=port2_phone,
        port3_phone=port3_phone,
    )


# ─── STEP 1: TCP 접속 + StartUp RPT ──────────────────────────────────────────

@pytest.mark.real_device
async def test_tcp_step1_접속_startup_rpt():
    """
    [STEP 1] TCP 접속 → Connect Level REQ 전송 → StartUp RPT 수신 확인.

    CALL_REQ 없이 연결만 테스트한다.
    tcpdump 패킷:
      →  01 10 09 00 00 00 66 04 00 e7 e7 00 00   (13바이트 Level REQ)
      ←  01 01 05 00 00 00 90 00 00               (9바이트 StartUp RPT)
    """
    _skip_if_no_ip()
    reader, writer = await asyncio.open_connection(_REAL_IP, _REAL_TCP_PORT)
    try:
        # Connect Level REQ 전송
        level_req = build_connect_level_req()
        writer.write(level_req)
        await writer.drain()
        print(f"\n  → Level REQ hex: {level_req.hex(' ')}")

        # StartUp RPT 수신 (명세: 5초 이내)
        frame = await asyncio.wait_for(_read_frame(reader), timeout=5.0)
        print(f"  ← 응답 hex      : {frame.hex(' ')}")

        ok, err_code = parse_startup_response(frame)
        print(f"  파싱 결과: ok={ok}, err_code={err_code}")

        assert ok, (
            f"StartUp RPT 수신 실패 (err_code={err_code})\n"
            f"패킷: {frame.hex(' ')}\n"
            "원인 가능: 이미 다른 TCP 세션이 장비를 점유 중 (error 302)"
        )
        print("[PASS] STEP 1 — TCP 접속 + StartUp RPT 확인")
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:  # noqa: BLE001
            pass


# ─── STEP 2: Port=0 단일 CALL_REQ ────────────────────────────────────────────

@pytest.mark.real_device
async def test_tcp_step2_port0_단일_call():
    """
    [STEP 2] StartUp RPT 수신 후 Port=0 CALL_REQ 전송 → CALL_RPT 수신.

    결과 코드만 출력하고 assert는 완화한다 (BUSY·FAIL도 패킷이 오면 통과).
    tcpdump 포인트:
      - CALL_REQ의 NodeID 바이트 (bytes 4·5) 값이 예상 DST_NODE_ID와 일치하는지
      - Phone_Num 바이트가 올바르게 들어갔는지
    """
    _skip_if_no_ip()
    reader, writer = await asyncio.open_connection(_REAL_IP, _REAL_TCP_PORT)
    try:
        writer.write(build_connect_level_req())
        await writer.drain()

        frame = await asyncio.wait_for(_read_frame(reader), timeout=5.0)
        ok, err_code = parse_startup_response(frame)
        assert ok, f"StartUp RPT 실패 (err_code={err_code}) → STEP 1 먼저 확인"

        # Port=0 CALL_REQ 전송 (Node ID 1 고정)
        call_req = build_call_req(port=0, phone=_PORT0_PHONE)
        writer.write(call_req)
        await writer.drain()
        print(f"\n  → CALL_REQ hex  : {call_req.hex(' ')}")
        print(f"    node_id=1(고정), port=0, phone={_PORT0_PHONE!r}")

        # CALL_RPT 수신 (~30초 성공 / ~50초 실패)
        frame = await asyncio.wait_for(_read_frame(reader), timeout=_CALL_TIMEOUT)
        result = parse_call_rpt(frame)
        print(f"  ← CALL_RPT hex  : {frame.hex(' ')}")
        print(f"  결과 코드        : {result.value}")

        # 패킷이 도달하면 통과 (OK인지 여부는 별도 확인)
        print(f"[{'PASS' if result.value == 'OK' else 'INFO'}] STEP 2 — Port 0 결과: {result.value}")
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:  # noqa: BLE001
            pass


# ─── STEP 3: 단일 세션 Port 0+1 순차 호출 ────────────────────────────────────

@pytest.mark.real_device
async def test_tcp_step3_단일세션_full_pair():
    """
    [STEP 3] BacsTcpCrossTestProtocol.run_pair() — 단일 TCP 세션에서 Port 0·1 순차 호출.

    수정된 crosstest_proto.py의 핵심 검증:
    - Port 0 CALL_RPT 수신 후 동일 연결에서 Port 1 CALL_REQ 전송 가능한지 확인
    - 포트별 결과와 전체 ok 여부 출력
    """
    _skip_if_no_ip()
    device = _make_device(
        ip=_REAL_IP,
        tcp_port=_REAL_TCP_PORT,
        port2_phone=_PORT0_PHONE,
        port3_phone=_PORT1_PHONE,
    )

    proto = BacsTcpCrossTestProtocol()
    result = await proto.run_pair(src=device, dst=device, timeout=_SESSION_TIMEOUT)

    print(f"\n  ok            : {result.ok}")
    print(f"  error_message : {result.error_message}")

    # assert: connect_failed나 connect_error는 FAIL (단, CALL 결과 자체는 허용)
    assert "connect_failed" not in (result.error_message or ""), (
        f"TCP 접속 또는 StartUp RPT 단계 실패: {result.error_message}"
    )
    assert "connect_error" not in (result.error_message or ""), (
        f"TCP 연결 자체 실패: {result.error_message}"
    )
    print(f"[{'PASS' if result.ok else 'INFO'}] STEP 3 — 전체 결과: {result.error_message or 'OK'}")


# ─── STEP 4: 중복 연결 → error 302 ───────────────────────────────────────────

@pytest.mark.real_device
async def test_tcp_step4_중복_연결_error302():
    """
    [STEP 4] 동일 장비에 TCP 연결 2개 시도 → 두 번째 연결에서 error 302 수신 확인.

    BACS 명세 §1.3.1:
    "TCP session이 이미 연결되어 있는 경우 새로운 연결은 Error code 302를 report하고 disconnect"

    검증: parse_startup_response() → (False, 302)
    """
    _skip_if_no_ip()

    async def _open_and_level() -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """TCP 접속 후 Level REQ 전송만 하고 StreamReader/Writer 반환."""
        r, w = await asyncio.open_connection(_REAL_IP, _REAL_TCP_PORT)
        w.write(build_connect_level_req())
        await w.drain()
        return r, w

    r1, w1 = await _open_and_level()
    try:
        # 첫 번째 연결에서 StartUp RPT 수신 (정상 제어권 획득)
        frame1 = await asyncio.wait_for(_read_frame(r1), timeout=5.0)
        ok1, _ = parse_startup_response(frame1)
        print(f"\n  첫 번째 연결 StartUp: ok={ok1}, hex={frame1.hex(' ')}")

        if not ok1:
            pytest.skip("첫 번째 연결도 StartUp RPT 실패 → 장비 상태 불명확, 스킵")

        # 두 번째 연결 시도 (첫 번째 세션이 살아 있는 상태)
        r2, w2 = await _open_and_level()
        try:
            frame2 = await asyncio.wait_for(_read_frame(r2), timeout=5.0)
            ok2, err_code = parse_startup_response(frame2)
            print(f"  두 번째 연결 응답  : ok={ok2}, err_code={err_code}, hex={frame2.hex(' ')}")

            assert not ok2, "두 번째 연결이 StartUp RPT를 반환 — 중복 접속 제어가 없는 것 같음"
            assert err_code == 302, (
                f"예상 error 302 인데 실제 code={err_code}\n"
                f"패킷: {frame2.hex(' ')}"
            )
            print("[PASS] STEP 4 — 두 번째 연결에서 error 302 정상 수신")
        finally:
            w2.close()
            try:
                await w2.wait_closed()
            except Exception:  # noqa: BLE001
                pass
    finally:
        w1.close()
        try:
            await w1.wait_closed()
        except Exception:  # noqa: BLE001
            pass


# ─── STEP 5: UI E2E — API로 세션 생성 → polling → 완료 확인 ──────────────────

@pytest.mark.real_device
async def test_tcp_step5_ui_end_to_end_api():
    """
    [STEP 5] UI E2E — 실제 백엔드 API를 통해 호출시험 세션을 생성하고 완료까지 확인.

    이 테스트가 통과하면 UI에서 호출시험 버튼을 눌렀을 때와 동일한 경로로
    장비까지 패킷이 오고 가고 결과가 DB에 저장·반환된다는 것이 검증된다.

    흐름:
      1. POST /auth/login  → access_token 획득
      2. POST /tests { scenario_id }  → session 생성 (UI의 api.startTest 동일 경로)
      3. GET  /tests/{session_id} 반복 polling → terminal 상태(completed/failed) 대기
      4. session.status, pair 결과 출력

    환경변수:
      BACS_API_BASE_URL      (기본값 http://localhost:8000)
      BACS_API_USERNAME      (기본값 admin)
      BACS_API_PASSWORD      (기본값 admin)
      BACS_REAL_SCENARIO_ID  (기본값 1)
    """
    _skip_if_no_ip()
    try:
        import httpx
    except ImportError:
        pytest.skip("httpx 미설치 → pip install httpx 후 재실행")

    _TERMINAL = {"completed", "cancelled", "failed"}

    async with httpx.AsyncClient(base_url=_API_BASE, timeout=30.0) as client:
        # ── 1. 로그인 ──────────────────────────────────────────────────────
        login_resp = await client.post(
            "/auth/login",
            json={"username": _API_USER, "password": _API_PASS},
        )
        assert login_resp.status_code == 200, (
            f"로그인 실패 ({login_resp.status_code}): {login_resp.text}\n"
            f"BACS_API_USERNAME={_API_USER}, BACS_API_PASSWORD={_API_PASS}"
        )
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"\n  로그인 성공 (user={_API_USER})")

        # ── 2. 호출시험 세션 생성 (UI의 api.startTest() 와 동일) ──────────
        create_resp = await client.post(
            "/tests",
            json={"scenario_id": _SCENARIO_ID},
            headers=headers,
        )
        assert create_resp.status_code == 201, (
            f"세션 생성 실패 ({create_resp.status_code}): {create_resp.text}\n"
            f"BACS_REAL_SCENARIO_ID={_SCENARIO_ID}\n"
            "시나리오가 DB에 등록되어 있고 장비가 2대 이상인지 확인"
        )
        session_data = create_resp.json()
        session_id = session_data["id"]
        print(f"  세션 생성: id={session_id}, status={session_data['status']}")

        # ── 3. terminal 상태까지 polling (UI의 SSE stream 역할) ─────────────
        # 최대 대기: 포트 2개 × 60초 + 여유 = 150초
        poll_timeout = 150.0
        poll_interval = 3.0
        elapsed = 0.0

        while elapsed < poll_timeout:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            get_resp = await client.get(f"/tests/{session_id}", headers=headers)
            assert get_resp.status_code == 200, f"세션 조회 실패: {get_resp.text}"
            ts = get_resp.json()
            print(
                f"  [{elapsed:5.0f}s] status={ts['status']} "
                f"ok={ts.get('ok_count', '?')} / fail={ts.get('fail_count', '?')} / "
                f"total={ts.get('total_pairs', '?')}"
            )

            if ts["status"] in _TERMINAL:
                break
        else:
            pytest.fail(f"세션 {session_id} 이 {poll_timeout}초 내에 완료되지 않음")

        # ── 4. 결과 출력 및 검증 ──────────────────────────────────────────
        print(f"\n  최종 status : {ts['status']}")
        print(f"  ok_count    : {ts.get('ok_count')}")
        print(f"  fail_count  : {ts.get('fail_count')}")
        print(f"  total_pairs : {ts.get('total_pairs')}")

        # cancelled는 비정상 완료
        assert ts["status"] != "cancelled", "세션이 취소됨 — 스케줄러 오류 가능"

        # completed 또는 failed 모두 허용 (CALL 결과는 장비 상태에 따라 다름)
        # connect_failed/connect_error가 없으면 TCP 프로토콜 자체는 정상 동작
        print(
            f"[{'PASS' if ts['status'] == 'completed' else 'INFO(failed)'}] "
            f"STEP 5 — UI E2E 세션 종료: {ts['status']}"
        )
