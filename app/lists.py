"""Manual ordering for the side panels (drag & drop).

Kept separate from the board's `.order.json`:
- `.order.json` is **one global total order** (fractional ranks) for the board;
- `.lists.json` stores **one list per panel**: Focus is rule-sorted by default,
  Watch is split by file, Someday is a flat card list — the default orders are
  different, so they cannot share a single ranking.

```json
{"focus": ["T-1", "T-2"], "watch:shows": ["T-3"], "someday": ["T-4", "- 2026-10-20 — an idea"]}
```

List keys: the task ID when there is one; otherwise the raw line (used by free
bullets in someday). The key is stable as long as that line does not change.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from parser import Task

LISTS_FILE = Path(
    os.environ.get("LISTS_FILE", str(Path(__file__).with_name(".lists.json")))
)


def load(path: Path | None = None) -> dict[str, list[str]]:
    """Load every panel order. Missing or broken file means empty — default order stands."""
    target = path or LISTS_FILE
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, list[str]] = {}
    for scope, keys in raw.items():
        if isinstance(scope, str) and isinstance(keys, list):
            out[scope] = [str(k) for k in keys]
    return out


def save(scope: str, keys: list[str], path: Path | None = None) -> list[str]:
    """Replace one panel's order wholesale (the client sends the full order after a drag)."""
    target = path or LISTS_FILE
    data = load(target)
    data[scope] = [str(k) for k in keys]

    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(tmp, target)
    return data[scope]


def key_of(task: Task) -> str:
    """Stable identifier inside a list: the ID when present, otherwise the raw line."""
    return task.id or task.raw


def sort_by(tasks: list[Task], keys: list[str]) -> list[Task]:
    """Sort by the saved list; tasks missing from it keep their original order at the end."""
    if not keys:
        return tasks
    index = {k: i for i, k in enumerate(keys)}
    tail = len(index)
    return sorted(tasks, key=lambda t: index.get(key_of(t), tail))
