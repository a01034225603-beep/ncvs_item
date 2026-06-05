import asyncio
import struct

from app.protocol.constants import (
    MSG_CONNECT_RPT,
    TYPE_MA_SE_CNTL,
    TYPE_SE_MA_CNTL,
)

# ─── TCP 응답 패킷 상수 (BACS_Control.md §1.3 기준) ─────────────────────────

# MA_SE_Start_Up_RPT (9바이트): 01 01 05 00 00 00 90 00 00
_TCP_STARTUP_RPT: bytes = bytes([0x01, 0x01, 0x05, 0x00, 0x00, 0x00, 0x90, 0x00, 0x00])

# MA_SE_Error_RPT (err_code=302, no msg string): 11바이트
def _build_error_rpt(err_code: int) -> bytes:
    """MA_SE_Error_RPT 패킷 빌드 (err_code만 포함, msg string 없음)."""
    data_len = 5 + 2  # NodeID(2)+MsgType(1)+MsgDataLen(2) + ErrCode(2)
    return struct.pack("<HH", 0x0101, data_len) + struct.pack("<HBH", 0, 0x91, 2) + struct.pack("<H", err_code)

# MA_SE_CALL_RPT 빌드 헬퍼
def _build_call_rpt(node_id: int, port: int, result_code: int) -> bytes:
    """MA_SE_CALL_RPT 패킷 빌드 (11바이트).

    실장비 확인 결과: MsgData = Port(1바이트) + ResultCode(1바이트)
    예) Port 0 OK: 00 11 / Port 1 OK: 01 11
    """
    # 01 02 | 07 00 | NodeID(2,LE) | d0 | 02 00 | port(1) | result(1)
    return (
        struct.pack("<HH", 0x0201, 7)
        + struct.pack("<HBH", node_id, 0xD0, 2)
        + bytes([port & 0xFF, result_code & 0xFF])
    )

_CALL_RESULT_OK   = 0x11
_CALL_RESULT_NK   = 0x13
_CALL_RESULT_BUSY = 0x15
_CALL_RESULT_FAIL = 0x23


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


# ─── Fake BACS TCP 서버 ───────────────────────────────────────────────────────

class FakeBacsTcp:
    """
    테스트용 BACS TCP 서버 시뮬레이터.

    동작:
      1. 클라이언트 접속 수신
      2. Connect Level REQ 읽기
      3. startup_ok=True → MA_SE_Start_Up_RPT 전송
         startup_ok=False → MA_SE_Error_RPT(err_code) 전송 후 연결 종료
      4. CALL_REQ(Port=0) 읽기 → CALL_RPT(call_results[0]) 전송
      5. CALL_REQ(Port=1) 읽기 → CALL_RPT(call_results[1]) 전송
      6. 연결 종료
    """

    def __init__(
        self,
        startup_ok: bool = True,
        startup_error_code: int = 302,
        call_results: tuple[int, int] = (_CALL_RESULT_OK, _CALL_RESULT_OK),
        call_delay_sec: float = 0.0,
    ) -> None:
        self.startup_ok = startup_ok
        self.startup_error_code = startup_error_code
        self.call_results = call_results
        self.call_delay_sec = call_delay_sec
        # 수신된 패킷 기록 (테스트 검증용)
        self.received_packets: list[bytes] = []
        self._server: asyncio.AbstractServer | None = None

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            # Connect Level REQ 수신 (4바이트 헤더 읽기 → DataLength만큼 추가 읽기)
            header = await reader.readexactly(4)
            data_len = int.from_bytes(header[2:4], "little")
            body = await reader.readexactly(data_len)
            self.received_packets.append(header + body)

            if not self.startup_ok:
                # 연결 거부 — Error RPT 전송 후 종료
                writer.write(_build_error_rpt(self.startup_error_code))
                await writer.drain()
                return

            # StartUp RPT 전송
            writer.write(_TCP_STARTUP_RPT)
            await writer.drain()

            # 두 포트 CALL_REQ 수신 → CALL_RPT 전송
            for idx, result_code in enumerate(self.call_results):
                header = await reader.readexactly(4)
                data_len = int.from_bytes(header[2:4], "little")
                body = await reader.readexactly(data_len)
                self.received_packets.append(header + body)

                if self.call_delay_sec > 0:
                    await asyncio.sleep(self.call_delay_sec)

                # Node ID와 포트 번호는 수신 패킷에서 추출
                node_id = int.from_bytes(body[0:2], "little")
                req_port = body[5] if len(body) > 5 else idx  # CALL_REQ MsgData[0] = port
                writer.write(_build_call_rpt(node_id, req_port, result_code))
                await writer.drain()

        except (asyncio.IncompleteReadError, ConnectionResetError):
            pass
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:  # noqa: BLE001
                pass

    async def start(self, host: str = "127.0.0.1", port: int = 0) -> int:
        """서버 시작. 실제 바인드된 포트 번호를 반환."""
        self._server = await asyncio.start_server(self._handle, host, port)
        return self._server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()
