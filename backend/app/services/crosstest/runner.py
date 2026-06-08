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

        # ── 트랜잭션 1: 페어 상태 확정 (ok/fail) — 반드시 성공해야 함 ──────
        # increment_counters 와 분리된 독립 세션으로 실행.
        # 이 트랜잭션이 롤백되면 pair.status 가 "running" 에 고착되어
        # 프론트엔드에 "영원히 실행 중" 으로 표시되는 버그가 발생하므로
        # 재시도 로직을 포함한다.
        for _attempt in range(3):
            try:
                async with self.session_factory() as db:
                    await pair_repo.mark_result(
                        db, item.pair_id, ok=result.ok, error=result.error_message
                    )
                    await db.commit()
                break  # 성공 시 재시도 루프 탈출
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "crosstest.pair.mark_result_retry attempt={} session={} pair={} err={}",
                    _attempt + 1, item.session_id, item.pair_id, exc,
                )
                await asyncio.sleep(0.1 * (_attempt + 1))  # 지수 백오프

        # ── 트랜잭션 2: 최신 결과 갱신 + 세션 카운터 증분 ────────────────
        # 원자적 UPDATE SQL 사용으로 데드락 확률이 낮지만, 실패해도
        # pair 상태(트랜잭션 1)에는 영향 없음 — 통계 오차만 발생
        try:
            async with self.session_factory() as db:
                await pair_repo.upsert_latest(
                    db,
                    src_bacs_id=item.src_id,
                    dst_bacs_id=item.dst_id,
                    ok=result.ok,
                    error=result.error_message,
                    session_id=item.session_id,
                )
                await session_repo.increment_counters(db, item.session_id, ok=result.ok)
                await db.commit()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "crosstest.pair.stats_save_failed session={} pair={} err={}",
                item.session_id, item.pair_id, exc,
            )
        finally:
            # ── 트랜잭션 3: device_locks 해제 — 항상 실행 ────────────────
            # 앞선 트랜잭션 실패와 무관하게 잠금은 반드시 해제한다.
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
