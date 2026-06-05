"""
TCP 호출시험 프로토콜 통합 테스트
fake_bacs TCP 서버를 사용하여 실제 소켓 통신으로 검증

TDD: 각 시나리오를 먼저 정의, BacsTcpCrossTestProtocol로 검증
"""
import pytest
import pytest_asyncio
from types import SimpleNamespace

from app.protocol.crosstest_proto import BacsTcpCrossTestProtocol
from tests.simulator.fake_bacs import (
    FakeBacsTcp,
    _CALL_RESULT_BUSY,
    _CALL_RESULT_FAIL,
    _CALL_RESULT_NK,
    _CALL_RESULT_OK,
)


def _make_device(ip: str, port: int, **phones) -> SimpleNamespace:
    """
    테스트용 장비 객체 생성 헬퍼.

    SQLAlchemy BacsDevice 대신 SimpleNamespace 사용:
    - BacsDevice.__new__() 는 ORM 매퍼 미초기화로 AttributeError 발생
    - FakeBacsTcp 는 전화번호를 실제 다이얼하지 않으므로 phone=None 허용
    - 실장비 테스트(test_tcp_real.py)에서만 실제 전화번호 환경변수로 주입
    - node_id 는 항상 1 고정이므로 여기서 받지 않음
    """
    return SimpleNamespace(
        id=1,
        name=f"test-{ip}",
        ip_address=ip,
        udp_port=7788,
        tcp_port=port,
        location=None,
        enabled=True,
        port0_phone=phones.get("port0_phone"),
        port1_phone=phones.get("port1_phone"),
        port2_phone=phones.get("port2_phone"),   # FakeBacsTcp는 내용 무관
        port3_phone=phones.get("port3_phone"),   # FakeBacsTcp는 내용 무관
    )


@pytest.mark.asyncio
class TestBacsTcpCrossTestProtocol:

    async def test_정상_호출시험_성공(self):
        """두 포트 모두 OK → PairResult(ok=True)"""
        server = FakeBacsTcp(call_results=(_CALL_RESULT_OK, _CALL_RESULT_OK))
        port = await server.start()
        try:
            src = _make_device("127.0.0.1", port)
            dst = _make_device("127.0.0.1", port)  # phone=None: FakeBacsTcp는 내용 무관
            proto = BacsTcpCrossTestProtocol()
            result = await proto.run_pair(src, dst, timeout=10.0)
            assert result.ok is True
            assert result.error_message is None
        finally:
            await server.stop()

    async def test_포트0_실패_포트1_성공(self):
        """TX0 실패 → ok=False, 실패 상세 포함"""
        server = FakeBacsTcp(call_results=(_CALL_RESULT_FAIL, _CALL_RESULT_OK))
        port = await server.start()
        try:
            src = _make_device("127.0.0.1", port)
            dst = _make_device("127.0.0.1", port)
            proto = BacsTcpCrossTestProtocol()
            result = await proto.run_pair(src, dst, timeout=10.0)
            assert result.ok is False
            assert "TX0" in result.error_message
            assert "FAIL" in result.error_message
        finally:
            await server.stop()

    async def test_포트0_성공_포트1_실패(self):
        """TX1 실패 → ok=False, TX1 상세 포함"""
        server = FakeBacsTcp(call_results=(_CALL_RESULT_OK, _CALL_RESULT_NK))
        port = await server.start()
        try:
            src = _make_device("127.0.0.1", port)
            dst = _make_device("127.0.0.1", port)
            proto = BacsTcpCrossTestProtocol()
            result = await proto.run_pair(src, dst, timeout=10.0)
            assert result.ok is False
            assert "TX1" in result.error_message
            assert "NK" in result.error_message
        finally:
            await server.stop()

    async def test_두_포트_모두_실패(self):
        """둘 다 실패 → ok=False, 두 포트 상세 모두 포함"""
        server = FakeBacsTcp(call_results=(_CALL_RESULT_BUSY, _CALL_RESULT_FAIL))
        port = await server.start()
        try:
            src = _make_device("127.0.0.1", port)
            dst = _make_device("127.0.0.1", port)
            proto = BacsTcpCrossTestProtocol()
            result = await proto.run_pair(src, dst, timeout=10.0)
            assert result.ok is False
            assert "TX0" in result.error_message
            assert "TX1" in result.error_message
        finally:
            await server.stop()

    async def test_접속_거부_error302(self):
        """StartUp 대신 Error 302 → ok=False, connect_failed 포함"""
        server = FakeBacsTcp(startup_ok=False, startup_error_code=302)
        port = await server.start()
        try:
            src = _make_device("127.0.0.1", port)
            dst = _make_device("127.0.0.1", port)
            proto = BacsTcpCrossTestProtocol()
            result = await proto.run_pair(src, dst, timeout=10.0)
            assert result.ok is False
            assert "connect_failed" in result.error_message
        finally:
            await server.stop()

    async def test_연결_실패_OSError(self):
        """존재하지 않는 포트 → ok=False, connect_error 포함"""
        src = _make_device("127.0.0.1", 19999)  # 닫힌 포트
        dst = _make_device("127.0.0.1", 19999)
        proto = BacsTcpCrossTestProtocol()
        result = await proto.run_pair(src, dst, timeout=5.0)
        assert result.ok is False
        assert "connect_error" in result.error_message

    async def test_call_req_패킷_2개_전송_확인(self):
        """fake server가 CALL_REQ 2개를 수신했는지 확인 (Connect Level REQ 포함 총 3개)"""
        server = FakeBacsTcp(call_results=(_CALL_RESULT_OK, _CALL_RESULT_OK))
        port = await server.start()
        try:
            src = _make_device("127.0.0.1", port)
            dst = _make_device("127.0.0.1", port)
            proto = BacsTcpCrossTestProtocol()
            await proto.run_pair(src, dst, timeout=10.0)
            # Connect Level REQ(1) + CALL_REQ x2 = 3개 수신
            assert len(server.received_packets) == 3
        finally:
            await server.stop()

    async def test_전화번호_없을때_정상_동작(self):
        """phone_number가 None이어도 패킷 전송 자체는 정상"""
        server = FakeBacsTcp(call_results=(_CALL_RESULT_OK, _CALL_RESULT_OK))
        port = await server.start()
        try:
            src = _make_device("127.0.0.1", port)
            dst = _make_device("127.0.0.1", port, port2_phone=None, port3_phone=None)
            proto = BacsTcpCrossTestProtocol()
            result = await proto.run_pair(src, dst, timeout=10.0)
            assert result.ok is True
        finally:
            await server.stop()
