"""Parsing layer: scan `tasks/` and turn markdown task lines into structured data.

Read-only: this module never writes files (see `writer.py` for writes and
`order.py` for ordering). The contract lives in
`skill/quadrant/references/md-conventions.md`.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Callable

import synonyms as syn

# ---------------------------------------------------------------- configuration

# Scan root. Exactly one root by design; the env var exists for tests and for
# pointing at an existing notes directory.
# Default: <repo>/tasks (the parent of app/), created by scripts/init_tasks.py.
TASKS_ROOT = Path(
    os.environ.get("TASKS_ROOT") or str(Path(__file__).resolve().parent.parent / "tasks")
)

# The board only reads 1-active: 0-inbox (raw capture) and 4-someday (later)
# are still part of tasks/, they are simply never shown on the board.
INCLUDE_FILES: tuple[str, ...] = ()
INCLUDE_DIRS = ("1-active",)

# Second track: follow lists (shows, serials, books in progress).
# They have no P/U and no DDL; putting them in a quadrant would be semantic
# pollution, so they get their own panel tab.
# Directory is semantics: everything under `follow/` is kind=follow and never
# shows up in board filters or counts.
# Directory name(s) for the follow track. Comma-separated in FOLLOW_DIRS, so a data
# directory that already uses a localized name (e.g. a Chinese folder) works without
# hard-coding it in the source.
# FOLLOW_DIRS is the current name; WATCH_DIRS is the pre-rename name and still honoured,
# so a launcher written before the rename keeps working instead of showing an empty panel.
FOLLOW_DIR_NAMES = os.environ.get("FOLLOW_DIRS") or os.environ.get("WATCH_DIRS") or "follow"
FOLLOW_DIRS: tuple[str, ...] = tuple(
    part.strip() for part in FOLLOW_DIR_NAMES.split(",") if part.strip()
)
# Third track: someday (ideas / "not now"). A single file, also outside the board.
SOMEDAY_FILES: tuple[str, ...] = ("4-someday.md",)
KIND_TASK = "task"
KIND_FOLLOW = "follow"
KIND_SOMEDAY = "someday"
ALL_KINDS: tuple[str, ...] = (KIND_TASK, KIND_FOLLOW, KIND_SOMEDAY)

# Not scanned: long notes / timeline log / archive / templates
EXCLUDE_DIRS = {"2-notes", "3-log", "5-archive", ".obsidian", ".git"}
EXCLUDE_FILES = {"README.md"}
EXCLUDE_PREFIXES = ("_",)  # _project-template.md, _note-template.md

# The log directory is exposed separately: for writing logs, not for scanning
LOG_DIR = "3-log"

STATUS_MAP = {" ": "todo", "x": "done", "X": "done", "-": "blocked"}
STATUS_LABEL = {"todo": "To do", "done": "Done", "blocked": "Blocked"}

UNCLASSIFIED = "unclassified"

QUADRANT_LABEL = {
    "Q1": "Q1 Important & urgent",
    "Q2": "Q2 Important, not urgent",
    "Q3": "Q3 Urgent, not important",
    "Q4": "Q4 Neither",
    UNCLASSIFIED: "Unclassified (missing P or U)",
}

# Due buckets (used for **grouping**): mutually exclusive, otherwise one task
# would show up in two groups at once.
DUE_LABEL = {
    "overdue": "Overdue",
    "today": "Due today",
    "week": "Next 7 days",
    "later": "Later",
    "none": "No DDL",
}

# `due` as a **filter** uses a different definition (see DUE_FILTER below):
# grouping must be exclusive, but "this week" should intuitively include today
# (a rolling 7 days), so the filter set is wider.
DUE_FILTER = {
    "today": {"today"},
    "week": {"today", "week"},
    "overdue": {"overdue"},
    "none": {"none"},
}

# ---------------------------------------------------------------- regexes

# Task line: only a **flush-left** `- [ ]` starts a new task; an indented one is
# detail for the task above it.
TASK_RE = re.compile(r"^- \[([ xX-])\](?:[ \t]+(.*))?$")
# Loose variant: "looks like a task line". Used to report lines that look right
# but failed to parse (see find_suspicious).
LOOSE_TASK_RE = re.compile(r"^- \[[ xX-]\]")
# ID: T- + YYMMDD + - + daily sequence number
ID_RE = re.compile(r"^T-\d{6}-\d+$")
ID_PARTS_RE = re.compile(r"^T-(\d{6})-(\d+)$")
# Tags: `#` followed by non-space, non-# characters; CJK, `/` and `-` allowed
# (e.g. #later/someday, #cheatsheet)
TAG_RE = re.compile(r"#([^\s#]+)")
# DDL: day precision only; a trailing time is tolerated when reading but never
# written by the app.
DDL_RE = re.compile(r"DDL:(\d{4}-\d{2}-\d{2})(?:[ T](\d{2}:\d{2}))?")
DONE_RE = re.compile(r"DONE:(\d{4}-\d{2}-\d{2})")
# Block reference at end of line: ^T-xxx
BLOCKREF_RE = re.compile(r"(?:^|\s)\^(T-\d{6}-\d+)\s*$")
# [[...]] wiki links (reserved for 2-notes/ details)
LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")

# Field prefix used when a tag maps onto a structured field
PU_PREFIX = {"p": "P", "u": "U"}


# ---------------------------------------------------------------- data model


@dataclass
class Task:
    """One task. Four groups of fields: identity / contract / source anchor / derived.

    The source anchor (file / line / raw / detail) is what the writer relies on:
    the only reliable way to write back is "change exactly the line you meant to
    change".
    """

    # --- identity ---
    id: str | None
    status: str  # todo / done / blocked
    title: str

    # --- contract fields ---
    p: int | None = None  # importance 1-3 (#P1 = most important)
    u: int | None = None  # urgency 1-3 (#U1 = most urgent)
    tags: list[str] = field(default_factory=list)  # excludes #P1/#U1
    ddl: str | None = None  # ISO date
    ddl_time: str | None = None  # HH:MM (reserved, never written today)
    done: str | None = None  # ISO date
    block_ref: str | None = None  # trailing ^T-xxx
    links: list[str] = field(default_factory=list)  # [[T-xxx]]

    # --- track ---
    kind: str = KIND_TASK  # task (board) / follow (list, never on the board)

    # --- source anchor ---
    file: str = ""  # path relative to tasks/
    project: str = ""  # file name without .md
    group_path: list[str] = field(default_factory=list)  # directory levels
    line: int = 0  # 1-based line number
    raw: str = ""  # original task line (no trailing newline)
    detail: list[str] = field(default_factory=list)  # indented detail lines, verbatim

    # --- derived ---
    quadrant: str = UNCLASSIFIED

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "status": self.status,
            "statusLabel": STATUS_LABEL.get(self.status, self.status),
            "title": self.title,
            "p": self.p,
            "u": self.u,
            "quadrant": self.quadrant,
            "quadrantLabel": QUADRANT_LABEL.get(self.quadrant, self.quadrant),
            "tags": self.tags,
            "ddl": self.ddl,
            "ddlTime": self.ddl_time,
            "done": self.done,
            "blockRef": self.block_ref,
            "links": self.links,
            "kind": self.kind,
            "file": self.file,
            "project": self.project,
            "groupPath": self.group_path,
            "line": self.line,
            "raw": self.raw,
            "detail": self.detail,
        }


# ---------------------------------------------------------------- scan scope


def iter_source_files(
    root: Path = TASKS_ROOT, kinds: tuple[str, ...] = ALL_KINDS
) -> list[Path]:
    """List the markdown files to scan, sorted (a stable order makes diffing sane).

    `kinds` selects tracks: task -> `1-active/`; follow -> `follow/`.
    The default scans both, because writes must be able to locate any task.
    """
    found: list[Path] = []

    if KIND_SOMEDAY in kinds:
        for name in SOMEDAY_FILES:
            p = root / name
            if p.is_file():
                found.append(p)

    for name in INCLUDE_FILES:
        p = root / name
        if p.is_file():
            found.append(p)

    dirs: list[str] = []
    if KIND_TASK in kinds:
        dirs.extend(INCLUDE_DIRS)
    if KIND_FOLLOW in kinds:
        dirs.extend(FOLLOW_DIRS)

    for dirname in dirs:
        base = root / dirname
        if not base.is_dir():
            continue
        for p in base.rglob("*.md"):
            rel_parts = p.relative_to(root).parts
            if any(part in EXCLUDE_DIRS for part in rel_parts):
                continue
            if p.name in EXCLUDE_FILES or p.name.startswith(EXCLUDE_PREFIXES):
                continue
            found.append(p)

    # Sort on the relative path string, not on Path objects: Path comparison is
    # case-insensitive on Windows and platform dependent. We want predictability.
    return sorted(found, key=lambda p: p.relative_to(root).as_posix())


# ---------------------------------------------------------------- parsing


def classify_tag(tag: str) -> tuple[str, int] | None:
    """`#P2` -> ("p", 2), `#u1` -> ("u", 1); anything else returns None (case-insensitive)."""
    if len(tag) == 2 and tag[0] in "PpUu" and tag[1] in "123":
        return ("p" if tag[0] in "Pp" else "u", int(tag[1]))
    return None


def parse_task_line(line: str) -> dict | None:
    """Parse one task line. Returns None for anything else (indented lines, blanks).

    Order matters: trailing metadata is stripped first, whatever remains is the
    title. Markdown inside the title (`**bold**`, links) is kept verbatim.
    """
    m = TASK_RE.match(line)
    if not m:
        return None

    status = STATUS_MAP[m.group(1)]
    rest = m.group(2) or ""

    # Trailing block reference ^T-xxx: parsed but never part of the title
    block_ref = None
    m_ref = BLOCKREF_RE.search(rest)
    if m_ref:
        block_ref = m_ref.group(1)
        rest = rest[: m_ref.start()]

    # Completion date
    done = None
    m_done = DONE_RE.search(rest)
    if m_done:
        done = m_done.group(1)
        rest = rest[: m_done.start()] + rest[m_done.end() :]

    # Due date (an optional time is tolerated)
    ddl = ddl_time = None
    m_ddl = DDL_RE.search(rest)
    if m_ddl:
        ddl, ddl_time = m_ddl.group(1), m_ddl.group(2)
        rest = rest[: m_ddl.start()] + rest[m_ddl.end() :]

    # Tags: P/U become fields, the rest go to tags (original case is preserved
    # for display)
    p = u = None
    tags: list[str] = []
    for tag in TAG_RE.findall(rest):
        hit = classify_tag(tag)
        if hit is None:
            tags.append(tag)
        elif hit[0] == "p":
            p = hit[1]
        else:
            u = hit[1]
    rest = TAG_RE.sub("", rest)

    # ID: only recognised as the first token, so a title that happens to look
    # like an ID is not swallowed
    task_id = None
    parts = rest.split(None, 1)
    if parts and ID_RE.match(parts[0]):
        task_id = parts[0]
        rest = parts[1] if len(parts) > 1 else ""

    title = " ".join(rest.split())
    links = LINK_RE.findall(title)

    return {
        "id": task_id,
        "status": status,
        "title": title,
        "p": p,
        "u": u,
        "tags": tags,
        "ddl": ddl,
        "ddl_time": ddl_time,
        "done": done,
        "block_ref": block_ref,
        "links": links,
    }


def quadrant_of(p: int | None, u: int | None) -> str:
    """Quadrant = P x U, computed on the fly. Missing a field means unclassified."""
    if p is None or u is None:
        return UNCLASSIFIED
    if p == 1 and u == 1:
        return "Q1"
    if p == 1:
        return "Q2"
    if u == 1:
        return "Q3"
    return "Q4"


def split_source_lines(text: str) -> list[str]:
    """Split on `\\n`, **keeping a trailing `\\r` on each line** (CRLF info is kept).

    `str.splitlines()` is not used on purpose: it also breaks on `\\x0b`,
    `\\u2028` and friends, which would change the line count.
    """
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()  # empty string produced by the trailing newline
    return lines


def parse_file(path: Path, root: Path = TASKS_ROOT) -> list[Task]:
    """Parse one markdown file. Indented lines belong to the nearest task above."""
    rel = path.relative_to(root).as_posix()
    project = path.stem
    parts = path.relative_to(root).parts
    group_path = list(parts[:-1])
    kind = KIND_TASK
    if parts and parts[0] in FOLLOW_DIRS:
        kind = KIND_FOLLOW
    elif path.name in SOMEDAY_FILES:
        kind = KIND_SOMEDAY

    if kind == KIND_SOMEDAY:
        return parse_someday_file(path, root)

    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        text = fh.read()

    tasks: list[Task] = []
    current: Task | None = None

    for lineno, raw in enumerate(split_source_lines(text), start=1):
        line = raw[:-1] if raw.endswith("\r") else raw

        parsed = parse_task_line(line)
        if parsed is not None:
            current = Task(
                **parsed,
                kind=kind,
                file=rel,
                project=project,
                group_path=group_path,
                line=lineno,
                raw=line,
                detail=[],
            )
            current.quadrant = quadrant_of(current.p, current.u)
            tasks.append(current)
            continue

        # Indented and non-empty -> detail of the previous task, verbatim
        if current is not None and line[:1] in (" ", "\t") and line.strip():
            current.detail.append(line)

    return tasks


def parse_someday_file(path: Path, root: Path = TASKS_ROOT) -> list[Task]:
    """Parse `4-someday.md`, which accepts two kinds of entries.

    - `- [ ] T-xxx title #P1 #U3 ...` -- parsed as a normal task line
      (these are items moved over from 1-active)
    - `- 2026-10-20 -- a one-line idea` -- an **ID-less idea**, the whole body
      becomes the title

    Indented lines always belong to the entry above (that is what the "open to
    read the full text" behaviour in the panel shows).
    Template lines (the literal `YYYY-MM-DD` placeholder) are skipped.
    """
    rel = path.relative_to(root).as_posix()
    project = path.stem
    group_path = list(path.relative_to(root).parts[:-1])

    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        text = fh.read()

    tasks: list[Task] = []
    current: Task | None = None

    for lineno, raw in enumerate(split_source_lines(text), start=1):
        line = raw[:-1] if raw.endswith("\r") else raw

        parsed = parse_task_line(line)
        if parsed is not None:
            current = Task(
                **parsed,
                kind=KIND_SOMEDAY,
                file=rel,
                project=project,
                group_path=group_path,
                line=lineno,
                raw=line,
                detail=[],
            )
            current.quadrant = quadrant_of(current.p, current.u)
            tasks.append(current)
            continue

        # Plain bullet: an ID-less idea entry
        if line.startswith("- "):
            body = line[2:].strip()
            if not body or "YYYY-MM-DD" in body:  # skip template lines
                current = None
                continue
            current = Task(
                id=None,
                status="todo",
                title=body,
                kind=KIND_SOMEDAY,
                file=rel,
                project=project,
                group_path=group_path,
                line=lineno,
                raw=line,
                detail=[],
            )
            tasks.append(current)
            continue

        if current is not None and line[:1] in (" ", "\t") and line.strip():
            current.detail.append(line)

    return tasks


def load_tasks(
    root: Path = TASKS_ROOT, kinds: tuple[str, ...] = ALL_KINDS
) -> list[Task]:
    """Scan the given tracks, parse, and sort by the default order (ID order)."""
    tasks: list[Task] = []
    for path in iter_source_files(root, kinds):
        tasks.extend(parse_file(path, root))
    tasks.sort(key=default_rank)
    return tasks


def find_duplicate_ids(tasks: list[Task]) -> list[dict]:
    """Report IDs that occur more than once.

    Duplicates break the "locate by ID" contract the writer relies on, so the UI
    surfaces them with a one-click repair. Occurrences are ordered by file and line,
    and the first one is the one that keeps the ID.
    """
    groups: dict[str, list[Task]] = {}
    for t in tasks:
        if t.id:
            groups.setdefault(t.id, []).append(t)

    out: list[dict] = []
    for task_id, items in groups.items():
        if len(items) < 2:
            continue
        items.sort(key=lambda t: (t.file, t.line))
        out.append(
            {
                "id": task_id,
                "count": len(items),
                "occurrences": [
                    {"file": t.file, "line": t.line, "title": t.title} for t in items
                ],
            }
        )
    return sorted(out, key=lambda g: g["id"])


def keyword_pred(q: str, groups: list[list[str]] | None = None) -> Predicate:
    """Public alias of the keyword predicate, for panels that only need search."""
    return _keyword_pred(q, groups)


def find_suspicious(root: Path = TASKS_ROOT) -> list[dict]:
    """Reconcile: flush-left lines that look like tasks but fail TASK_RE.

    Typical cause: a missing space after `- [ ]`. Such lines are otherwise
    dropped silently, so they are reported in the UI instead.
    """
    out: list[dict] = []
    for path in iter_source_files(root):
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            text = fh.read()
        for lineno, raw in enumerate(split_source_lines(text), start=1):
            line = raw[:-1] if raw.endswith("\r") else raw
            if LOOSE_TASK_RE.match(line) and not TASK_RE.match(line):
                out.append(
                    {
                        "file": path.relative_to(root).as_posix(),
                        "line": lineno,
                        "raw": line,
                    }
                )
    return out


# ---------------------------------------------------------------- order (defaults)

# The real ordering layer is `order.py`. This only provides the default used
# when no order record exists: derive it from the ID (T-YYMMDD-N -> (YYMMDD, N)),
# i.e. creation order.


def default_rank(task: Task) -> tuple:
    """Default order: ascending ID; entries without an ID go last."""
    if task.id:
        m = ID_PARTS_RE.match(task.id)
        if m:
            return (0, int(m.group(1)), int(m.group(2)), task.file, task.line)
    return (1, 0, 0, task.file, task.line)


def id_rank(task: Task) -> float:
    """Turn the ID into a comparable float, in the same units as `order.py` ranks."""
    if task.id:
        m = ID_PARTS_RE.match(task.id)
        if m:
            return (int(m.group(1)) * 1000 + int(m.group(2))) * 1024.0
    # No ID: fall back to file + line, which is stable and sorts last
    return 10**15 + hash((task.file, task.line)) % 1000


# ---------------------------------------------------------------- search (predicates)

# Filtering is a list of (Task -> bool) predicates: adding a filter means adding
# a pure function, with no UI change.

Predicate = Callable[[Task], bool]


def _keyword_pred(q: str, groups: list[list[str]] | None = None) -> Predicate:
    """Keyword: matches **title / detail lines / tags / project / directory / ID**,
    case-insensitively.

    Title and detail alone are not enough: "where does this belong" often lives
    in tags and file names. Searching `#garden` should find the task filed under
    `1-active/life/garden.md`.

    With a synonym table the term is expanded to its whole group first, so
    searching "camping" also finds tasks tagged "outdoors". A leading `#` is
    stripped, so `#reading` and `reading` are equivalent.
    """
    groups = syn.load_groups() if groups is None else groups
    needles = syn.expand(q, groups)

    def pred(t: Task) -> bool:
        # group_path[1:] skips the outer "1-active", otherwise searching it would
        # match every single task
        hay = "\n".join(
            [t.title, *t.detail, *t.tags, t.project, t.id or "", *t.group_path[1:]]
        ).lower()
        return any(n in hay for n in needles)

    return pred


def _tag_pred(wanted: list[str], mapping: dict[str, str] | None = None) -> Predicate:
    """Tags: **case-insensitive**, several tags are OR-ed.

    Tags that are equivalent in the synonym table count as one (picking #TopN
    also brings in #focus).
    """
    mapping = syn.build_mapping(syn.load_groups()) if mapping is None else mapping
    wanted_keys = {syn.canonical(w, mapping) for w in wanted}

    def pred(t: Task) -> bool:
        return any(syn.canonical(tag, mapping) in wanted_keys for tag in t.tags)

    return pred


def due_bucket(task: Task, today: date) -> str:
    """Bucket a task by due date (**mutually exclusive**, used for grouping):
    overdue / today / week / later / none."""
    if task.ddl is None:
        return "none"
    d = date.fromisoformat(task.ddl)
    if task.status != "done" and d < today:
        return "overdue"
    if d == today:
        return "today"
    if today < d <= today + timedelta(days=6):
        return "week"
    return "later"


def month_pred(today: date) -> Predicate:
    """Calendar month (unlike the rolling 7 days used by `week`)."""

    def pred(t: Task) -> bool:
        if t.ddl is None:
            return False
        d = date.fromisoformat(t.ddl)
        return (d.year, d.month) == (today.year, today.month)

    return pred


def make_filters(
    *,
    q: str | None,
    p: list[int] | None,
    u: list[int] | None,
    tag: list[str] | None,
    status: list[str] | None,
    project: list[str] | None,
    dirs: list[str] | None,
    due: str | None,
    include_done: bool,
    today: date,
    groups: list[list[str]] | None = None,
) -> list[Predicate]:
    """Turn query parameters into a list of predicates. Date logic always uses the
    `today` passed in for this request."""
    preds: list[Predicate] = []
    groups = syn.load_groups() if groups is None else groups
    mapping = syn.build_mapping(groups)

    if q and q.strip():
        preds.append(_keyword_pred(q, groups))
    if p:
        preds.append(lambda t: t.p in p)
    if u:
        preds.append(lambda t: t.u in u)
    if tag:
        preds.append(_tag_pred(tag, mapping))
    if status:
        want = set(status)
        preds.append(lambda t: t.status in want)
    elif not include_done:
        # Default to **to-do** only: done and blocked ([-]) are hidden.
        # Pass status=blocked explicitly to see blocked items.
        preds.append(lambda t: t.status == "todo")
    if project:
        want = set(project)
        preds.append(lambda t: t.project in want)
    if dirs:
        # Directory filter matches by **prefix**, so picking "1-active/work" pulls
        # in every file below it. The empty string "" means the root directory
        # (files such as 0-inbox.md or 4-someday.md).
        picked = [d.strip("/") for d in dirs]

        def _dir_pred(t: Task, picked: list[str] = picked) -> bool:
            for d in picked:
                if d == "":
                    if not t.group_path:
                        return True
                elif t.file == d:  # a specific file was picked
                    return True
                elif t.file.startswith(d + "/"):
                    return True
            return False

        preds.append(_dir_pred)
    if due:
        allowed = DUE_FILTER.get(due)
        if allowed is not None:
            preds.append(lambda t: due_bucket(t, today) in allowed)

    return preds


# ---------------------------------------------------------------- grouping


def group_of(task: Task, mode: str, today: date) -> tuple[str, str, int]:
    """Return (group key, display label, sort position).

    Note: there is **no group-by-tag**. Tags overlap, so one task would appear in
    several groups at once. Tags filter; they never group.
    """
    if mode == "none":
        return ("all", "All tasks", 0)
    if mode == "quadrant":
        order = {"Q1": 0, "Q2": 1, "Q3": 2, "Q4": 3, UNCLASSIFIED: 4}
        return (task.quadrant, QUADRANT_LABEL[task.quadrant], order[task.quadrant])
    if mode == "p9":
        # 3x3 grid of P x U: one row per P, one column per U
        if task.p is None or task.u is None:
            return ("PU-", "Unclassified", 9)
        key = f"P{task.p}U{task.u}"
        return (key, f"P{task.p}·U{task.u}", (task.p - 1) * 3 + (task.u - 1))
    if mode == "project":
        return (task.project, task.project, 0)
    if mode == "file":
        return (task.file, task.file, 0)
    if mode == "p":
        key = f"P{task.p}" if task.p else "P-"
        label = (
            f"P{task.p} ({'most important' if task.p == 1 else 'least important' if task.p == 3 else 'medium'})"
            if task.p
            else "No P"
        )
        return (key, label, task.p if task.p else 9)
    if mode == "u":
        key = f"U{task.u}" if task.u else "U-"
        label = (
            f"U{task.u} ({'most urgent' if task.u == 1 else 'least urgent' if task.u == 3 else 'medium'})"
            if task.u
            else "No U"
        )
        return (key, label, task.u if task.u else 9)
    if mode == "status":
        order = {"todo": 0, "blocked": 1, "done": 2}
        return (task.status, STATUS_LABEL.get(task.status, task.status), order.get(task.status, 9))
    if mode == "due":
        order = {"overdue": 0, "today": 1, "week": 2, "later": 3, "none": 4}
        b = due_bucket(task, today)
        return (b, DUE_LABEL[b], order[b])
    raise ValueError(f"unknown group mode: {mode}")


GROUP_MODES = ("none", "p9", "quadrant", "project", "file", "p", "u", "status", "due")

# Skeleton of the 3x3 grid (the UI draws empty cells too)
P9_CELLS = [f"P{p}U{u}" for p in (1, 2, 3) for u in (1, 2, 3)]


# ---------------------------------------------------------------- Focus view


def focus_score(task: Task, today: date) -> tuple:
    """Focus ordering:

    overdue (oldest first) -> due today -> P1+U1 -> P1 -> U1 -> nearest DDL -> rank
    """
    overdue = 0
    if task.ddl:
        d = date.fromisoformat(task.ddl)
        if task.status != "done" and d < today:
            overdue = 1
            days_late = -(d - today).days  # the larger, the older
        else:
            days_late = 0
    else:
        days_late = 0

    is_today = 1 if task.ddl == today.isoformat() else 0
    p1u1 = 1 if (task.p == 1 and task.u == 1) else 0
    p1 = 1 if task.p == 1 else 0
    u1 = 1 if task.u == 1 else 0
    ddl_near = date.fromisoformat(task.ddl).toordinal() if task.ddl else 10**7

    return (-overdue, -days_late, -is_today, -p1u1, -p1, -u1, ddl_near)


def is_focus(task: Task, groups: list[list[str]] | None = None) -> bool:
    """Selection uses the literal tag `#TopN` (case-insensitive).

    With a synonym table, `#focus` qualifies too when the table maps them together.
    """
    groups = syn.load_groups() if groups is None else groups
    mapping = syn.build_mapping(groups)
    key = syn.canonical("TopN", mapping)
    return any(syn.canonical(tag, mapping) == key for tag in task.tags)


def dir_tree(tasks: list[Task]) -> list[dict]:
    """Directory -> task count. The empty string "" is the root directory.

    Directories only, no files: the UI builds the tree itself.
    """
    counts: dict[str, int] = {}
    for t in tasks:
        parts = t.group_path
        if not parts:
            # Files at the root (0-inbox.md / 4-someday.md) are counted
            # separately, matching the dirs=[""] convention in make_filters
            counts[""] = counts.get("", 0) + 1
            continue
        for i in range(1, len(parts) + 1):
            key = "/".join(parts[:i])
            counts[key] = counts.get(key, 0) + 1
    return [{"path": k, "count": v} for k, v in sorted(counts.items())]


# ---------------------------------------------------------------- tag merging


def collect_tags(tasks: list[Task], groups: list[list[str]] | None = None) -> list[dict]:
    """Tag merging: **case-insensitive matching, original casing for display**.

    Two merges happen at once:
    1. case variants (#React / #react) become one, labelled with the most
       frequent spelling
    2. synonym-equivalent tags (#TopN / #focus) become one
    """
    groups = syn.load_groups() if groups is None else groups
    mapping = syn.build_mapping(groups)

    merged: dict[str, dict] = {}
    for t in tasks:
        for tag in t.tags:
            key = syn.canonical(tag, mapping)
            entry = merged.get(key)
            if entry is None:
                entry = merged[key] = {"key": key, "count": 0, "labels": {}}
            entry["count"] += 1
            entry["labels"][tag] = entry["labels"].get(tag, 0) + 1

    out = []
    for entry in merged.values():
        # The most frequent spelling becomes the label; ties break alphabetically
        # so the result is stable
        label = sorted(entry["labels"].items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        out.append({"key": entry["key"], "label": label, "count": entry["count"]})
    return sorted(out, key=lambda e: (-e["count"], e["label"]))
