from typing import Protocol


class _PairLike(Protocol):
    id: int
    src_bacs_id: int
    dst_bacs_id: int


def pick_next_dispatchable(pairs, locked_devices: set[int]):
    """Return the first pair whose src and dst are both unlocked, or None."""
    for pair in pairs:
        src = getattr(pair, "src_bacs_id", None) or getattr(pair, "src", None)
        dst = getattr(pair, "dst_bacs_id", None) or getattr(pair, "dst", None)
        if src in locked_devices or dst in locked_devices:
            continue
        return pair
    return None
