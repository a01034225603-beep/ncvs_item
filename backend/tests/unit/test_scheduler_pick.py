from dataclasses import dataclass

from app.services.crosstest.scheduler import pick_next_dispatchable


@dataclass
class _P:
    """실제 TestSessionPair 모델의 최소 서브셋 (테스트 전용)."""
    id: int
    src_bacs_id: int
    dst_bacs_id: int


def test_picks_first_pair_when_no_locks():
    pairs = [_P(1, 10, 20), _P(2, 30, 40)]
    chosen = pick_next_dispatchable(pairs, locked_devices=set())
    assert chosen is not None
    assert chosen.id == 1


def test_skips_pairs_that_touch_locked_device():
    pairs = [_P(1, 10, 20), _P(2, 30, 40)]
    chosen = pick_next_dispatchable(pairs, locked_devices={10})
    assert chosen.id == 2


def test_returns_none_when_all_blocked():
    pairs = [_P(1, 10, 20), _P(2, 10, 30)]
    chosen = pick_next_dispatchable(pairs, locked_devices={10})
    assert chosen is None
