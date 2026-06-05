import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from loguru import logger

from app.models import BacsDevice
from app.protocol.tcp_messages import (
    CallResult,
    build_call_req,
    build_connect_level_req,
    is_error_rpt,
    parse_call_rpt,
    parse_error_rpt,
    parse_packet_for_display,
    parse_startup_response,
)

# TCP 접속 후 StartUp RPT 수신 대기 타임아웃 (명세: 5초 이내 미전송 시 자동 Close)
_CONNECT_TIMEOUT_SEC = 4.0
# CALL_RPT 수신 대기 타임아웃 (명세: 실패 응답 ~50초, pair_timeout은 70초로 별도 제어)
_CALL_RPT_TIMEOUT_SEC = 60.0
# 프레임 헤더 크기: Type(2) + DataLength(2)
_HEADER_SIZE = 4


@dataclass(frozen=True)
class PairResult:
    ok: bool
    error_message: str | None = None


# 패킷 이벤트 콜백 타입 — (direction, step, raw_bytes, pair_label) → None
EmitFn = Callable[[str, str, bytes, str], None]


class CrossTestProtocol(Protocol):
    async def run_pair(
        self,
        src: BacsDevice,
        dst: BacsDevice,
        timeout: float,
        emit: EmitFn | None = None,
    ) -> PairResult: ...


async def _read_frame(reader: asyncio.StreamReader) -> bytes:
    """
    TCP 스트림에서 패킷 1개를 완전히 읽어 반환한다.

    프레임 구조: Header(4바이트) + Data(DataLength바이트)
    Header의 DataLength 필드 기준으로 나머지를 읽는다.
    """
    header = await reader.readexactly(_HEADER_SIZE)
    # DataLength: Header[2:4] Little-endian
    data_len = int.from_bytes(header[2:4], "little")
    body = await reader.readexactly(data_len)
    return header + body


async def _tcp_session(
    host: str,
    port: int,
    port_pairs: list[tuple[int, str | None, str]],
    call_rpt_timeout: float,
    emit: "EmitFn | None" = None,
) -> list[tuple[bool, str]]:
    """
    src BACS에 TCP 접속하여 단일 세션에서 여러 포트 호출시험을 순차 수행한다.

    BACS 명세 §1.3.1: TCP session이 이미 연결되어 있으면 새 연결은 error 302로 거부된다.
    따라서 Port 0·Port 1을 반드시 같은 TCP 연결 안에서 처리해야 한다.

    Node ID는 항상 1 고정 (tcp_messages._CALL_NODE_ID).

    Args:
        host:             src BACS IP
        port:             src BACS TCP 포트 (보통 7788)
        port_pairs:       [(tx_port, rx_phone, port_label), ...] 순서대로 호출
                          port_label: UI 표시용 포트 레이블
                          (예: "192.168.1.10:Port0 → 192.168.1.11:Port2")
        call_rpt_timeout: CALL_RPT 수신 최대 대기 시간 (포트당)
        emit:             패킷 이벤트 콜백 — (direction, step, raw, port_label) → None

    Returns:
        [(ok, detail), ...] — port_pairs 와 동일 순서
    """
    def _emit_to(direction: str, step: str, raw: bytes, label: str) -> None:
        """emit 콜백이 설정된 경우에만 호출하는 내부 래퍼."""
        if emit is not None:
            try:
                emit(direction, step, raw, label)
            except Exception:  # noqa: BLE001
                pass  # 이벤트 발행 실패가 호출시험에 영향 주지 않도록

    reader, writer = await asyncio.open_connection(host, port)
    results: list[tuple[bool, str]] = []
    try:
        # ── Step 1: Connect Level REQ 전송 ───────────────────────────────
        req_raw = build_connect_level_req()
        writer.write(req_raw)
        await writer.drain()
        # CONNECT_REQ는 공유 TCP 핸드셰이크이므로 모든 포트 섹션에 표시
        for _, _, lbl in port_pairs:
            _emit_to("TX", "CONNECT_REQ", req_raw, lbl)

        # ── Step 2: StartUp RPT 또는 Error RPT 수신 ─────────────────────
        frame = await asyncio.wait_for(_read_frame(reader), timeout=_CONNECT_TIMEOUT_SEC)
        ok, err_code = parse_startup_response(frame)
        if not ok:
            err_str = f"error_code={err_code}" if err_code else "no_startup"
            for tx_port, _, lbl in port_pairs:
                _emit_to("RX", "ERROR_RPT", frame, lbl)
                results.append((False, f"Port{tx_port}→Port{tx_port + 2}: connect_failed({err_str})"))
            return results

        # STARTUP_RPT도 모든 포트 섹션에 표시
        for _, _, lbl in port_pairs:
            _emit_to("RX", "STARTUP_RPT", frame, lbl)

        # ── Step 3·4: 포트별 CALL_REQ 전송 → CALL_RPT 수신 (같은 세션) ──
        for tx_port, rx_phone, port_label in port_pairs:
            call_raw = build_call_req(port=tx_port, phone=rx_phone)
            writer.write(call_raw)
            await writer.drain()
            _emit_to("TX", f"CALL_REQ[Port={tx_port}]", call_raw, port_label)

            # CALL_RPT 수신 (~30초 성공 / ~50초 실패)
            # BACS가 ERROR_RPT로 거부하는 경우도 처리
            frame = await asyncio.wait_for(_read_frame(reader), timeout=call_rpt_timeout)

            if is_error_rpt(frame):
                # CALL_REQ를 ERROR_RPT로 거부 — 잘못된 전화번호·node_id·권한 문제 등
                err_code, err_text = parse_error_rpt(frame)
                _emit_to("RX", f"ERROR_RPT[after CALL_REQ Port={tx_port}]", frame, port_label)
                fail_msg = f"Port{tx_port}→Port{tx_port + 2}: ERROR_RPT(code={err_code}, '{err_text}')"
                results.append((False, fail_msg))
            else:
                call_result = parse_call_rpt(frame)
                _emit_to("RX", f"CALL_RPT[Port={tx_port}]", frame, port_label)
                if call_result == CallResult.OK:
                    results.append((True, "OK"))
                else:
                    results.append((False, f"Port{tx_port}→Port{tx_port + 2}: {call_result.value}"))

    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:  # noqa: BLE001
            pass

    return results


class BacsTcpCrossTestProtocol:
    """
    실제 BACS TCP 호출시험 프로토콜 구현.

    한 페어(src → dst)에 대해 단일 TCP 세션에서:
      1) src에 TCP 접속 → Connect Level REQ → StartUp RPT 확인
      2) CALL_REQ (Port=0, Phone=dst.port2_phone) → CALL_RPT 수신
      3) CALL_REQ (Port=1, Phone=dst.port3_phone) → CALL_RPT 수신
         ↑ 같은 TCP 연결 안에서 순차 처리 (BACS 명세: 중복 연결 시 error 302 거부)
      4) 두 포트 모두 OK → PairResult(ok=True)
         하나라도 실패 → PairResult(ok=False, error_message=실패 상세)

    CALL_REQ의 Node ID는 항상 1 고정 (BACS 프로토콜 명세 기준).
    """

    async def run_pair(
        self,
        src: BacsDevice,
        dst: BacsDevice,
        timeout: float,
        emit: "EmitFn | None" = None,
    ) -> PairResult:
        src_ip = src.ip_address
        dst_ip = dst.ip_address
        logger.info("tcp_crosstest.start src={} dst={}", src_ip, dst_ip)

        # 포트별 레이블: UI에서 4개 세션으로 구분 표시
        #   Port 0 (TX) → Port 2 (RX), Port 1 (TX) → Port 3 (RX)
        port_pairs: list[tuple[int, str | None, str]] = [
            (0, dst.port2_phone, f"{src_ip}:Port0 → {dst_ip}:Port2"),
            (1, dst.port3_phone, f"{src_ip}:Port1 → {dst_ip}:Port3"),
        ]

        try:
            # 단일 TCP 세션에서 Port 0·1 순차 처리 (Node ID 1 고정)
            call_results = await asyncio.wait_for(
                _tcp_session(
                    host=src_ip,
                    port=src.tcp_port,
                    port_pairs=port_pairs,
                    call_rpt_timeout=_CALL_RPT_TIMEOUT_SEC,
                    emit=emit,
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            return PairResult(ok=False, error_message="session timeout")
        except OSError as exc:
            return PairResult(ok=False, error_message=f"connect_error({exc})")

        all_ok = True
        details: list[str] = []
        for ok, detail in call_results:
            if ok:
                details.append(detail)
                logger.info(
                    "tcp_crosstest.ok src={} dst={} detail={}",
                    src_ip, dst_ip, detail,
                )
            else:
                all_ok = False
                details.append(detail)
                logger.warning(
                    "tcp_crosstest.fail src={} dst={} detail={}",
                    src_ip, dst_ip, detail,
                )

        error_msg = " / ".join(details) if not all_ok else None
        return PairResult(ok=all_ok, error_message=error_msg)
