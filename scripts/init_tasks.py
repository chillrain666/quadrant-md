#!/usr/bin/env python3
"""Copy the template directory into your data directory (idempotent: skips if present,
never overwrites).

    python scripts/init_tasks.py                  # default: repo/tasks
    python scripts/init_tasks.py --root D:/todo   # elsewhere (point TASKS_ROOT at it)

The template lives in `templates/tasks/`: a directory hierarchy, demo data and the
format contract.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TEMPLATE = REPO / "templates" / "tasks"


def init(target: Path, template: Path = TEMPLATE) -> tuple[bool, str]:
    """Copy the template. Returns (created, message); does nothing if the target exists."""
    if not template.is_dir():
        raise FileNotFoundError(f"template directory not found: {template}")
    if target.exists():
        return False, f"already exists, skipped: {target}"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(template, target)
    return True, f"created: {target}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Initialise the tasks data directory")
    ap.add_argument("--root", default=str(REPO / "tasks"), help="data directory (default: repo/tasks)")
    args = ap.parse_args(argv)

    created, msg = init(Path(args.root))
    print(msg)
    if created:
        print("next: uv run python app/main.py   -> http://127.0.0.1:8000")
    return 0


if __name__ == "__main__":
    sys.exit(main())
