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
