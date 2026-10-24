"""Tests for scripts/init_tasks.py: temp directories only."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("init_tasks", ROOT / "scripts" / "init_tasks.py")
assert _spec and _spec.loader
init_tasks = importlib.util.module_from_spec(_spec)
sys.modules["init_tasks"] = init_tasks
_spec.loader.exec_module(init_tasks)


def test_init_copies_template():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "tasks"
        created, _ = init_tasks.init(target)
        assert created is True
        # The directory hierarchy is complete
        for rel in (
            "0-inbox.md",
            "1-active",
            "2-notes",
            "3-log",
            "4-someday.md",
            "5-archive",
            "follow",
            "README.md",
        ):
            assert (target / rel).exists(), rel
        # The sample tasks in the template parse into tasks
        sys.path.insert(0, str(ROOT / "app"))
        import parser as P

        tasks = P.load_tasks(kinds=(P.KIND_TASK,), root=target)
        assert len(tasks) >= 8
        assert all(t.id for t in tasks)


def test_init_is_idempotent_and_never_overwrites():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "tasks"
        init_tasks.init(target)
        marker = target / "0-inbox.md"
        marker.write_text("my own content\n", encoding="utf-8")

        created, msg = init_tasks.init(target)
        assert created is False
        assert "skip" in msg.lower()
        # Not a single byte of user data was touched
        assert marker.read_text(encoding="utf-8") == "my own content\n"


def test_init_rejects_missing_template():
    with tempfile.TemporaryDirectory() as tmp:
        try:
            init_tasks.init(Path(tmp) / "tasks", template=Path(tmp) / "nope")
        except FileNotFoundError:
            return
        raise AssertionError("a missing template must raise")
