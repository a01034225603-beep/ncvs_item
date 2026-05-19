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
