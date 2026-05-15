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
