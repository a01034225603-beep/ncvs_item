import asyncio
from dataclasses import dataclass

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.protocol.crosstest_proto import CrossTestProtocol, PairResult
from app.protocol.tcp_messages import parse_packet_for_display
from app.repositories import lock_repo, pair_repo, session_repo
from app.services import packet_log
from app.services.packet_log import PacketEvent


@dataclass
class WorkItem:
    pair_id: int
    session_id: int
    src_id: int
    dst_id: int


class PairRunner:
    def __init__(
        self,
        proto: CrossTestProtocol,
        session_factory: async_sessionmaker[AsyncSession],
        pair_timeout: float,
    ) -> None:
        self.proto = proto
        self.session_factory = session_factory
        self.pair_timeout = pair_timeout

    async def run(self, item: WorkItem, src, dst) -> PairResult:
        async with self.session_factory() as db:
            await pair_repo.mark_running(db, item.pair_id)
            await db.commit()

        logger.info("crosstest.pair.start session={} pair={}", item.session_id, item.pair_id)

        # ── 패킷 이벤트 콜백 빌드 ────────────────────────────────────────
        session_id = item.session_id

        def emit(direction: str, step: str, raw: bytes, pair_label: str) -> None:
            """TCP 패킷 송수신 시마다 호출 — PacketEvent를 세션 큐에 투입."""
            event = PacketEvent(
                session_id=session_id,
                pair_label=pair_label,
                direction=direction,
                step=step,
                hex_dump=raw.hex(" "),
                parsed=parse_packet_for_display(raw),
            )
            packet_log.publish(session_id, event)

        try:
            result = await self.proto.run_pair(src, dst, timeout=self.pair_timeout, emit=emit)
        except asyncio.TimeoutError:
            result = PairResult(ok=False, error_message="pair timeout")
        except Exception as exc:  # noqa: BLE001
            result = PairResult(ok=False, error_message=str(exc)[:255])

        # ── 결과 기록 (데드락으로 실패해도 lock 해제는 반드시 수행) ─────
        try:
            async with self.session_factory() as db:
                await pair_repo.mark_result(
                    db, item.pair_id, ok=result.ok, error=result.error_message
                )
                await pair_repo.upsert_latest(
                    db,
                    src_bacs_id=item.src_id,
                    dst_bacs_id=item.dst_id,
                    ok=result.ok,
                    error=result.error_message,
                    session_id=item.session_id,
                )
                # 원자적 증분 SQL — 동시 다수 완료 시 데드락 방지
                await session_repo.increment_counters(db, item.session_id, ok=result.ok)
                await db.commit()
        except Exception as exc:  # noqa: BLE001
            # 결과 기록 실패는 로그만 남기고 lock 해제는 반드시 진행
            logger.warning(
                "crosstest.pair.result_save_failed session={} pair={} err={}",
                item.session_id, item.pair_id, exc,
            )
        finally:
            # device_locks 해제는 메인 트랜잭션과 완전히 분리된 독립 세션
            # — 메인 트랜잭션 데드락 롤백 시에도 고아 잠금 레코드 방지
            async with self.session_factory() as db:
                await lock_repo.remove(db, item.src_id)
                await lock_repo.remove(db, item.dst_id)
                await db.commit()

        logger.info(
            "crosstest.pair.{} session={} pair={}",
            "ok" if result.ok else "fail",
            item.session_id,
            item.pair_id,
        )
        return result
