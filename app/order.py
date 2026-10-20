"""Ordering layer: one global total order; markdown never stores any order.

Three design rules:
1. **Defaults derived from the ID**: with no order record, the order is creation
   time (encoded in `T-YYMMDD-N`), so the UI is fully correct even when
   `.order.json` does not exist.
2. **Only dragged items are stored**: `{"T-261018-3": 2.5}`; every other task
   costs zero bytes.
3. **Disposable at any time**: delete the file and you are back to ID order;
   nothing in the content is lost.

Drop semantics: the moved task is placed **flush against the anchor** C. The
neighbours used are the *global* ones (previous/next in the whole list), not the
ones visible in the current view.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from parser import Task, id_rank

ORDER_FILE = Path(
    os.environ.get("ORDER_FILE", str(Path(__file__).with_name(".order.json")))
)
STEP = 1024.0

_lock = threading.Lock()


# ---------------------------------------------------------------- read / write


def load_overrides() -> dict[str, float]:
    """Read the rank overrides. Missing or broken file means empty: this is derived
    data and must never take the main flow down."""
    if not ORDER_FILE.is_file():
        return {}
    try:
        raw = json.loads(ORDER_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, float] = {}
    for k, v in raw.items():
        if isinstance(k, str) and isinstance(v, (int, float)):
            out[k] = float(v)
    return out


def save_overrides(overrides: dict[str, float]) -> None:
    """Atomic write: temp file + os.replace, so a crash cannot leave half a file."""
    tmp = ORDER_FILE.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(overrides, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(tmp, ORDER_FILE)


def prune(tasks: list[Task], overrides: dict[str, float]) -> dict[str, float]:
    """Drop ids that no longer exist (deleted from markdown) so the file stays small."""
    alive = {t.id for t in tasks if t.id}
    return {k: v for k, v in overrides.items() if k in alive}


# ---------------------------------------------------------------- sorting


def rank_of(task: Task, overrides: dict[str, float]) -> float:
    """Override wins; otherwise fall back to the value derived from the ID."""
    if task.id and task.id in overrides:
        return overrides[task.id]
    return id_rank(task)


def rank_map(tasks: list[Task], overrides: dict[str, float] | None = None) -> dict[str, float]:
    overrides = load_overrides() if overrides is None else overrides
    return {t.id: rank_of(t, overrides) for t in tasks if t.id}


def sort_tasks(tasks: list[Task], overrides: dict[str, float] | None = None) -> list[Task]:
    overrides = load_overrides() if overrides is None else overrides
    return sorted(tasks, key=lambda t: (rank_of(t, overrides), t.file, t.line))


# ---------------------------------------------------------------- drag & drop


def move(
    tasks: list[Task],
    mover_id: str,
    anchor_id: str,
    position: str,
) -> dict:
    """Move `mover` immediately before/after `anchor`.

    position: "before" | "after"

    Algorithm: take the global list without the mover, find the anchor, and pick
    a rank between the anchor and the neighbour on the drop side. The mover
    therefore always lands flush against the anchor, even when the neighbour is
    hidden by the current filters.
    """
    if position not in ("before", "after"):
        raise ValueError("position must be 'before' or 'after'")
    if mover_id == anchor_id:
        return {"changed": False, "reason": "mover and anchor are the same task"}

    with _lock:
        overrides = load_overrides()
        overrides = prune(tasks, overrides)
        ordered = sort_tasks(tasks, overrides)

        by_id = {t.id: t for t in ordered if t.id}
        if mover_id not in by_id:
            raise KeyError(f"task not found: {mover_id}")
        if anchor_id not in by_id:
            raise KeyError(f"anchor task not found: {anchor_id}")

        rest = [t for t in ordered if t.id != mover_id]
        i = next(idx for idx, t in enumerate(rest) if t.id == anchor_id)
        anchor = rest[i]

        lo = hi = None
        if position == "before":
            hi = rank_of(anchor, overrides)
            if i > 0:
                lo = rank_of(rest[i - 1], overrides)
        else:
            lo = rank_of(anchor, overrides)
            if i + 1 < len(rest):
                hi = rank_of(rest[i + 1], overrides)

        new_rank, rebalanced = _pick_rank(lo, hi)
        if rebalanced:
            # Float precision exhausted: renumber everything to 1024, 2048, 3072...
            # and compute the rank once more.
            overrides = _rebalance(ordered, overrides)
            ordered = sort_tasks(tasks, overrides)
            rest = [t for t in ordered if t.id != mover_id]
            i = next(idx for idx, t in enumerate(rest) if t.id == anchor_id)
            anchor = rest[i]
            lo = hi = None
            if position == "before":
                hi = rank_of(anchor, overrides)
                if i > 0:
                    lo = rank_of(rest[i - 1], overrides)
            else:
                lo = rank_of(anchor, overrides)
                if i + 1 < len(rest):
                    hi = rank_of(rest[i + 1], overrides)
            new_rank, _ = _pick_rank(lo, hi)

        overrides[mover_id] = new_rank
        save_overrides(overrides)

        return {
            "changed": True,
            "id": mover_id,
            "anchor": anchor_id,
            "position": position,
            "rank": new_rank,
            "rebalanced": rebalanced,
        }


def _pick_rank(lo: float | None, hi: float | None) -> tuple[float, bool]:
    """Pick a value between (lo, hi). Returns (rank, needs_rebalance)."""
    if lo is None and hi is None:
        return STEP, False
    if lo is None:  # very top of the global list
        return hi - STEP, False
    if hi is None:  # very end of the global list
        return lo + STEP, False
    mid = (lo + hi) / 2
    if not (lo < mid < hi):  # float precision exhausted
        return mid, True
    return mid, False


def _rebalance(ordered: list[Task], overrides: dict[str, float]) -> dict[str, float]:
    """Rewrite every rank as 1024, 2048, 3072... following the current order."""
    fresh: dict[str, float] = {}
    for idx, task in enumerate(ordered, start=1):
        if task.id:
            fresh[task.id] = idx * STEP
    save_overrides(fresh)
    return fresh
