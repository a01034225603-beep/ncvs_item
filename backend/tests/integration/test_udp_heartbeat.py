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
    # On Windows, UDP sends to a closed port trigger ICMP "port unreachable",
    # which the ProactorEventLoop surfaces as OSError (WinError 1234) rather
    # than letting wait_for() time out.  Accept all three plausible outcomes.
    with pytest.raises((asyncio.TimeoutError, ConnectionResetError, OSError)):
        await heartbeat("127.0.0.1", 1, timeout=0.2)  # nothing listening
