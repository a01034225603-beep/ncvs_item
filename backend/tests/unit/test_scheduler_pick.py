"""
test_scheduler_pick.py
pick_next_dispatchable 및 _assign_rounds 단위 테스트
"""
from dataclasses import dataclass, field

from app.services.crosstest.scheduler import pick_next_dispatchable
from app.services.session_service import _assign_rounds


@dataclass
class _P:
    """TestSessionPair 최소 서브셋 (테스트 전용)."""
    id: int
    src_bacs_id: int
    dst_bacs_id: int
    round_number: int = field(default=1)


# ── pick_next_dispatchable ──────────────────────────────────────────────────

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


def test_returns_none_for_empty_list():
    assert pick_next_dispatchable([], locked_devices=set()) is None


# ── _assign_rounds ──────────────────────────────────────────────────────────

def test_assign_rounds_no_conflict():
    """서로 겹치지 않는 페어 → 모두 라운드 1"""
    pairs = [(10, 20), (30, 40), (50, 60)]
    rounds = _assign_rounds(pairs)
    assert rounds == [1, 1, 1]


def test_assign_rounds_full_conflict():
    """모든 페어가 장비를 공유 → 각각 다른 라운드"""
    # A→B, A→C: A가 중복이므로 round 1, round 2 로 분리
    pairs = [(10, 20), (10, 30), (10, 40)]
    rounds = _assign_rounds(pairs)
    assert rounds[0] == 1
    assert rounds[1] == 2
    assert rounds[2] == 3


def test_assign_rounds_partial_conflict():
    """(A→B), (C→D): 겹침 없음 → round 1 / (A→C): A·C 공유 → round 2"""
    pairs = [(10, 20), (30, 40), (10, 30)]
    rounds = _assign_rounds(pairs)
    assert rounds[0] == 1  # A→B: round 1
    assert rounds[1] == 1  # C→D: round 1 (겹침 없음)
    assert rounds[2] == 2  # A→C: A(10)·C(30) 모두 round 1에 등장 → round 2


def test_assign_rounds_count():
    """라운드 번호는 1-based 이고, 최대 라운드 번호 = len(결과의 unique 값)"""
    pairs = [(1, 2), (1, 3), (1, 4)]
    rounds = _assign_rounds(pairs)
    assert min(rounds) == 1
    assert sorted(set(rounds)) == list(range(1, len(set(rounds)) + 1))
