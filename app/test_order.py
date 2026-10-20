"""Self-tests for order.py -- drop semantics of drag & drop.

Three things that must hold:
1. Default order = ID order (the UI is correct without .order.json)
2. A drop lands **flush against** the anchor, using global neighbours, not
   the ones visible in the current view
3. A drag never changes the relative order of the tasks that were not dragged

Run: uv run python test_order.py
"""

import tempfile
from contextlib import contextmanager
from pathlib import Path

import order as O
import parser as P

TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


@contextmanager
def temp_order():
    """Point .order.json at a temp file so the project one is never touched."""
    with tempfile.TemporaryDirectory() as d:
        old = O.ORDER_FILE
        O.ORDER_FILE = Path(d) / ".order.json"
        try:
            yield O.ORDER_FILE
        finally:
            O.ORDER_FILE = old


def T(seq: int, **kw) -> P.Task:
    return P.Task(
        id=f"T-261018-{seq}", status="todo", title=f"t{seq}",
        p=kw.get("p", 1), u=kw.get("u", 3), file="x.md", line=seq,
    )


def ids(tasks) -> list[str]:
    return [t.id.rsplit("-", 1)[1] for t in tasks]


# ---------------------------------------------------------------- default order


@test
def test_default_order_is_id_order():
    with temp_order():
        tasks = [T(10), T(2), T(33), T(1)]
        got = ids(O.sort_tasks(tasks))
        assert got == ["1", "2", "10", "33"], got  # numeric, not lexicographic


@test
def test_tasks_without_id_sort_last():
    with temp_order():
        a = T(1)
        b = P.Task(id=None, status="todo", title="no-id", file="x.md", line=99)
        got = [t.title for t in O.sort_tasks([b, a])]
        assert got == ["t1", "no-id"], got


@test
def test_broken_order_file_does_not_crash():
    with temp_order() as path:
        path.write_text("{ this is not json", encoding="utf-8")
        tasks = [T(2), T(1)]
        assert ids(O.sort_tasks(tasks)) == ["1", "2"]


# ---------------------------------------------------------------- drop: flush


@test
def test_drop_before_lands_flush_against_anchor():
    with temp_order():
        tasks = [T(i) for i in range(1, 6)]  # 1 2 3 4 5
        # Drag 5 before 3 -> it must sit right against 3, not somewhere in between
        O.move(tasks, "T-261018-5", "T-261018-3", "before")
        assert ids(O.sort_tasks(tasks)) == ["1", "2", "5", "3", "4"]


@test
def test_drop_after_lands_flush_against_anchor():
    with temp_order():
        tasks = [T(i) for i in range(1, 6)]
        O.move(tasks, "T-261018-1", "T-261018-3", "after")
        assert ids(O.sort_tasks(tasks)) == ["2", "3", "1", "4", "5"]


@test
def test_drop_skips_hidden_entries_without_a_gap():
    """Drag 1 before 4: it must sit against 4, not stay between 2 and 3."""
    with temp_order():
        tasks = [T(i) for i in range(1, 6)]
        O.move(tasks, "T-261018-1", "T-261018-4", "before")
        assert ids(O.sort_tasks(tasks)) == ["2", "3", "1", "4", "5"]


@test
def test_drop_at_very_top():
    with temp_order():
        tasks = [T(i) for i in range(1, 6)]
        res = O.move(tasks, "T-261018-5", "T-261018-1", "before")
        assert res["changed"] is True
        assert ids(O.sort_tasks(tasks)) == ["5", "1", "2", "3", "4"]


@test
def test_drop_at_very_end():
    with temp_order():
        tasks = [T(i) for i in range(1, 6)]
        O.move(tasks, "T-261018-1", "T-261018-5", "after")
        assert ids(O.sort_tasks(tasks)) == ["2", "3", "4", "5", "1"]


@test
def test_relative_order_of_others_never_changes():
    """The relative order of tasks that were not dragged never changes."""
    with temp_order():
        tasks = [T(i) for i in range(1, 7)]
        before = [t.id for t in O.sort_tasks(tasks) if t.id != "T-261018-6"]
        O.move(tasks, "T-261018-6", "T-261018-2", "after")
        after = [t.id for t in O.sort_tasks(tasks) if t.id != "T-261018-6"]
        assert before == after


@test
def test_drop_on_self_is_a_noop():
    with temp_order():
        tasks = [T(i) for i in range(1, 4)]
        res = O.move(tasks, "T-261018-2", "T-261018-2", "before")
        assert res["changed"] is False
        assert ids(O.sort_tasks(tasks)) == ["1", "2", "3"]


@test
def test_missing_task_raises():
    with temp_order():
        tasks = [T(1)]
        for mover, anchor in (("T-999", "T-261018-1"), ("T-261018-1", "T-999")):
            try:
                O.move(tasks, mover, anchor, "before")
            except KeyError:
                continue
            raise AssertionError(f"should have raised not-found: {mover} / {anchor}")


@test
def test_invalid_position_is_rejected():
    with temp_order():
        try:
            O.move([T(1), T(2)], "T-261018-1", "T-261018-2", "middle")
        except ValueError:
            return
        raise AssertionError("an invalid position must be rejected")


# ---------------------------------------------------------------- persistence


@test
def test_drop_persists_only_the_dragged_task():
    with temp_order() as path:
        tasks = [T(i) for i in range(1, 6)]
        O.move(tasks, "T-261018-5", "T-261018-1", "before")
        assert path.is_file()
        saved = O.load_overrides()
        assert list(saved) == ["T-261018-5"], saved
        # Re-reading the file keeps the order
        assert ids(O.sort_tasks(tasks)) == ["5", "1", "2", "3", "4"]


@test
def test_orphan_keys_are_pruned():
    with temp_order() as path:
        tasks = [T(1), T(2)]
        path.write_text('{"T-99999-1": 5.0, "T-261018-2": 42.0}', encoding="utf-8")
        O.move(tasks, "T-261018-1", "T-261018-2", "after")
        saved = O.load_overrides()
        assert "T-99999-1" not in saved, f"orphan key was not pruned: {saved}"
        assert "T-261018-2" in saved


# ---------------------------------------------------------------- precision


@test
def test_pick_rank_basics():
    assert O._pick_rank(None, None) == (O.STEP, False)
    assert O._pick_rank(None, 100.0) == (100.0 - O.STEP, False)
    assert O._pick_rank(100.0, None) == (100.0 + O.STEP, False)
    assert O._pick_rank(0.0, 100.0) == (50.0, False)


@test
def test_precision_exhaustion_triggers_rebalance():
    """Repeatedly insert into the same gap: after ~25 halvings the float gives up.
    A rebalance must happen automatically and the order must stay correct."""
    with temp_order():
        tasks = [T(i) for i in range(1, 41)]
        anchor = "T-261018-3"
        rebalanced = False
        for seq in range(4, 41):
            res = O.move(tasks, f"T-261018-{seq}", anchor, "before")
            rebalanced = rebalanced or res["rebalanced"]
            order = [t.id for t in O.sort_tasks(tasks)]
            idx = order.index(f"T-261018-{seq}")
            assert order[idx + 1] == anchor, f"#{seq} is not flush against the anchor: {order}"

        assert rebalanced, "37 insertions without a rebalance; the precision guard may be dead"

        # After the rebalance the order is still total and duplicate-free
        order = [t.id for t in O.sort_tasks(tasks)]
        assert len(order) == len(set(order)) == 40


@test
def test_ranks_strictly_increase():
    with temp_order():
        tasks = [T(i) for i in range(1, 8)]
        O.move(tasks, "T-261018-7", "T-261018-2", "before")
        O.move(tasks, "T-261018-1", "T-261018-5", "after")
        ordered = O.sort_tasks(tasks)
        ranks = [O.rank_of(t, O.load_overrides()) for t in ordered]
        assert ranks == sorted(ranks) and len(set(ranks)) == len(ranks), ranks


# ---------------------------------------------------------------- run


if __name__ == "__main__":
    failed = []
    for fn in TESTS:
        try:
            fn()
            print(f"  ok   {fn.__name__}")
        except Exception as exc:  # noqa: BLE001
            failed.append(fn.__name__)
            print(f"  FAIL {fn.__name__}: {type(exc).__name__}: {exc}")
    print(f"\n{len(TESTS) - len(failed)}/{len(TESTS)} passed")
    raise SystemExit(1 if failed else 0)
