"""Quadrant · backend entry point

    uv run python main.py          # start (also serves web/dist)
    uv run python -m uvicorn main:app --reload

Layers:
    parser.py  -- read-only: scan, parse, filter, group
    order.py   -- ordering: one global total order, stored in .order.json
                  (disposable)
    writer.py  -- write-back: create / retag / change status, touching only the
                  line that changed
    main.py    -- this file: the HTTP layer
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import order as order_mod
import lists as lists_mod
import parser as P
import synonyms as syn
import writer as W

app = FastAPI(
    title="Quadrant",
    version="1.0.0",
    description="A markdown-first local todo board (markdown is the single source of truth)",
)

DIST = Path(__file__).with_name("web") / "dist"


# ---------------------------------------------------------------- models


class TaskOut(BaseModel):
    """Task shape returned by the API. Must stay in sync with `parser.Task.to_dict()`
    (a test guards this)."""

    id: str | None
    status: str
    statusLabel: str
    title: str
    p: int | None
    u: int | None
    quadrant: str
    quadrantLabel: str
    tags: list[str]
    ddl: str | None
    ddlTime: str | None
    done: str | None
    blockRef: str | None
    links: list[str]
    kind: str
    file: str
    project: str
    groupPath: list[str]
    line: int
    raw: str
    detail: list[str]


class TaskGroup(BaseModel):
    key: str
    label: str
    count: int
    tasks: list[TaskOut]


class TasksResponse(BaseModel):
    today: str
    generatedAt: str
    tasksRoot: str
    total: int
    matched: int
    groupBy: str
    filters: dict
    groups: list[TaskGroup]


class NewTaskIn(BaseModel):
    file: str = Field(description="Target file, path relative to tasks/, e.g. 1-active/work/project.md")
    title: str = Field(min_length=1)
    p: int | None = Field(default=None, ge=1, le=3)
    u: int | None = Field(default=None, ge=1, le=3)
    tags: list[str] = Field(default_factory=list)
    ddl: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class StatusIn(BaseModel):
    status: Literal["todo", "done", "blocked"]


class TaskPatch(BaseModel):
    """Only send the fields you change: status when ticking, p+u when dragging,
    title/tags/ddl from the drawer.

    `ddl: null` clears the due date; leaving the key out means "do not touch it".
    `model_fields_set` is what tells the two apart.
    """

    status: Literal["todo", "done", "blocked"] | None = None
    p: int | None = Field(default=None, ge=1, le=3)
    u: int | None = Field(default=None, ge=1, le=3)
    title: str | None = None
    tags: list[str] | None = None
    ddl: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class AssignIdIn(BaseModel):
    """A task line that has no ID yet, identified by where it sits."""

    file: str
    line: int = Field(ge=1)
    raw: str


class MoveIn(BaseModel):
    id: str
    anchor: str
    position: Literal["before", "after"]


class ListOrderIn(BaseModel):
    """Full order of one panel after a drag (the client sends the finished key list)."""

    scope: str
    keys: list[str]


class SynonymsIn(BaseModel):
    """Synonym groups: each group needs at least two terms."""

    groups: list[list[str]]


# ---------------------------------------------------------------- shared helpers


def _load(
    kinds: tuple[str, ...] = P.ALL_KINDS,
) -> tuple[list[P.Task], dict[str, float]]:
    """Load every track by default (writes must be able to locate any task); the
    read endpoints filter by kind afterwards."""
    tasks = P.load_tasks(kinds=kinds)
    overrides = order_mod.load_overrides()
    return order_mod.sort_tasks(tasks, overrides), overrides


def _task_or_404(task_id: str) -> P.Task:
    try:
        task, _ = W.locate(P.TASKS_ROOT, task_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return task


# ---------------------------------------------------------------- read


@app.get("/api/tasks", response_model=TasksResponse)
def get_tasks(
    q: str | None = Query(
        None, description="Keyword: title / detail lines / tags / project / ID, case-insensitive"
    ),
    p: list[int] | None = Query(None, description="#P1/#P2/#P3; repeatable, any match"),
    u: list[int] | None = Query(None, description="#U1/#U2/#U3; repeatable, any match"),
    tag: list[str] | None = Query(None, description="Tags; repeatable, case-insensitive, any match"),
    status: list[str] | None = Query(
        None, description="todo / done / blocked; repeatable. Omit to hide done and blocked"
    ),
    project: list[str] | None = Query(None, description="Project (= file name without .md); repeatable"),
    dirs: list[str] | None = Query(
        None,
        alias="dir",
        description="Directory prefix; repeatable (OR), e.g. dir=1-active/work; dir= means the root",
    ),
    due: str | None = Query(
        None, pattern="^(today|week|month|overdue|none)$", description="Due window"
    ),
    include_done: bool = Query(False, description="Include done items (an explicit status wins)"),
    group_by: str = Query("none", description="Grouping: " + " / ".join(P.GROUP_MODES)),
    kind: str = Query("task", pattern="^(task|watch)$", description="Track: task (board) / watch (list)"),
):
    """Search + group. Order inside a group is the global rank, i.e. the dragged order."""
    if group_by not in P.GROUP_MODES:
        raise HTTPException(400, f"group_by must be one of: {' / '.join(P.GROUP_MODES)}")
    for name, values in (("p", p), ("u", u)):
        if values and any(v not in (1, 2, 3) for v in values):
            raise HTTPException(400, f"{name} must be 1, 2 or 3")

    today = date.today()  # date logic always uses today's real value

    ordered, overrides = _load(kinds=(kind,))
    preds = P.make_filters(
        q=q, p=p, u=u, tag=tag, status=status, project=project, dirs=dirs,
        due=due, include_done=include_done, today=today,
    )
    if due == "month":
        preds.append(P.month_pred(today))

    matched = [t for t in ordered if all(pred(t) for pred in preds)]

    buckets: dict[str, dict] = {}
    for t in matched:
        key, label, sort = P.group_of(t, group_by, today)
        entry = buckets.get(key)
        if entry is None:
            entry = buckets[key] = {"key": key, "label": label, "sort": sort, "tasks": []}
        entry["tasks"].append(t.to_dict())

    groups = sorted(buckets.values(), key=lambda g: (g["sort"], g["key"]))
    for g in groups:
        g.pop("sort")
        g["count"] = len(g["tasks"])

    return {
        "today": today.isoformat(),
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "tasksRoot": str(P.TASKS_ROOT),
        "total": len(ordered),
        "matched": len(matched),
        "groupBy": group_by,
        "filters": {
            "q": q, "p": p, "u": u, "tag": tag, "status": status,
            "project": project, "dir": dirs, "due": due, "includeDone": include_done,
            "kind": kind,
        },
        "groups": groups,
    }


@app.get("/api/watch", response_model=TasksResponse)
def get_watch(q: str | None = Query(None, description="Keyword, same rules as the board")):
    """Watch lists: grouped by file, **no P/U at all**.

    Done (watched) and blocked (dropped) entries are included -- a watch list is
    small, and seeing history is what makes it a list. Ordered by ID (the order
    items were added); no dragging.
    """
    ordered, _ = _load(kinds=(P.KIND_WATCH,))
    today = date.today()
    if q and q.strip():
        pred = P.keyword_pred(q)
        ordered = [t for t in ordered if pred(t)]

    buckets: dict[str, dict] = {}
    for t in ordered:
        entry = buckets.get(t.project)
        if entry is None:
            entry = buckets[t.project] = {
                "key": t.project,
                "label": t.project,
                "sort": len(buckets),
                "tasks": [],
                "count": 0,
            }
        entry["tasks"].append(t)
        entry["count"] += 1

    groups = sorted(buckets.values(), key=lambda g: (g["sort"], g["key"]))
    saved = lists_mod.load()
    for g in groups:
        g.pop("sort")
        g["tasks"] = [
            t.to_dict()
            for t in lists_mod.sort_by(g["tasks"], saved.get(f"watch:{g['key']}", []))
        ]

    return {
        "today": today.isoformat(),
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "tasksRoot": str(P.TASKS_ROOT),
        "total": len(ordered),
        "matched": len(ordered),
        "groupBy": "project",
        "filters": {"kind": P.KIND_WATCH},
        "groups": groups,
    }


@app.get("/api/someday", response_model=TasksResponse)
def get_someday(q: str | None = Query(None, description="Keyword, same rules as the board")):
    """Someday (ideas / not now): reads a single file, no P/U, no dragging.

    Two kinds of entries coexist: task lines with an ID and free bullets without one.
    """
    items = P.load_tasks(kinds=(P.KIND_SOMEDAY,))
    items = lists_mod.sort_by(items, lists_mod.load().get("someday", []))
    if q and q.strip():
        pred = P.keyword_pred(q)
        items = [t for t in items if pred(t)]
    today = date.today()

    return {
        "today": today.isoformat(),
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "tasksRoot": str(P.TASKS_ROOT),
        "total": len(items),
        "matched": len(items),
        "groupBy": "someday",
        "filters": {"kind": P.KIND_SOMEDAY},
        "groups": (
            [
                {
                    "key": "someday",
                    "label": "someday · ideas & later",
                    "count": len(items),
                    "tasks": [t.to_dict() for t in items],
                }
            ]
            if items
            else []
        ),
    }


@app.get("/api/meta")
def get_meta():
    """Raw material for the filters, plus a data self-check."""
    tasks, overrides = _load(kinds=(P.KIND_TASK,))
    today = date.today()
    watch_total = len(P.load_tasks(kinds=(P.KIND_WATCH,)))
    someday_total = len(P.load_tasks(kinds=(P.KIND_SOMEDAY,)))

    def tally(fn) -> dict[str, int]:
        out: dict[str, int] = {}
        for t in tasks:
            k = fn(t)
            out[k] = out.get(k, 0) + 1
        return out

    files = []
    file_counts: dict[str, int] = {}
    for t in tasks:
        file_counts[t.file] = file_counts.get(t.file, 0) + 1

    for path in P.iter_source_files(kinds=(P.KIND_TASK,)):
        rel = path.relative_to(P.TASKS_ROOT).as_posix()
        files.append(
            {
                "file": rel,
                "project": path.stem,
                "groupPath": list(path.relative_to(P.TASKS_ROOT).parts[:-1]),
                "count": file_counts.get(rel, 0),
            }
        )

    return {
        "today": today.isoformat(),
        "tasksRoot": str(P.TASKS_ROOT),
        "total": len(tasks),
        "tags": P.collect_tags(tasks),
        "synonyms": syn.load_groups(),
        "projects": sorted({t.project for t in tasks}),
        "dirs": P.dir_tree(tasks),
        "files": files,
        "status": tally(lambda t: t.status),
        "quadrant": tally(lambda t: t.quadrant),
        "p": tally(lambda t: f"P{t.p}" if t.p else "P-"),
        "u": tally(lambda t: f"U{t.u}" if t.u else "U-"),
        "due": tally(lambda t: P.due_bucket(t, today)),
        "focus": sum(1 for t in tasks if P.is_focus(t) and t.status != "done"),
        "watch": watch_total,
        "someday": someday_total,
        "overrides": len(overrides),
        # Self-check: lines that look like tasks but failed to parse
        "suspicious": P.find_suspicious(),
        # Self-check: IDs that appear more than once (block editing until repaired)
        "duplicateIds": P.find_duplicate_ids(P.load_tasks()),
    }


@app.put("/api/lists")
def put_list(body: ListOrderIn):
    """Persist one panel's manual order. Example scopes: focus / watch:shows / someday."""
    if not body.scope.strip():
        raise HTTPException(400, "scope cannot be empty")
    try:
        keys = lists_mod.save(body.scope, body.keys)
    except OSError as exc:
        raise HTTPException(500, f"write failed: {exc}") from exc
    return {"scope": body.scope, "count": len(keys)}


@app.get("/api/synonyms")
def get_synonyms():
    """Current synonym groups (the UI can read and edit them directly)."""
    return {"groups": syn.load_groups()}


@app.put("/api/synonyms")
def put_synonyms(body: SynonymsIn):
    """Replace the whole synonym table. The server sanitises it again: blanks and
    `#` removed, duplicates dropped, groups with fewer than two terms discarded."""
    try:
        return {"groups": syn.save_groups(body.groups)}
    except OSError as exc:
        raise HTTPException(500, f"write failed: {exc}") from exc


@app.get("/api/focus")
def get_focus(
    limit: int = Query(7, ge=1, le=50),
    q: str | None = Query(None, description="Keyword, same rules as the board"),
):
    """Focus view: unfinished tasks tagged `#TopN`, ordered by the Focus rules."""
    tasks, _ = _load(kinds=(P.KIND_TASK,))
    today = date.today()
    picked = [t for t in tasks if P.is_focus(t) and t.status == "todo"]
    if q and q.strip():
        pred = P.keyword_pred(q)
        picked = [t for t in picked if pred(t)]
    picked.sort(key=lambda t: P.focus_score(t, today))
    picked = lists_mod.sort_by(picked, lists_mod.load().get("focus", []))
    return {
        "today": today.isoformat(),
        "total": len(picked),
        "limit": limit,
        "tasks": [t.to_dict() for t in picked[:limit]],
    }


@app.post("/api/ids/assign", response_model=TaskOut)
def assign_id(body: AssignIdIn):
    """Fill in a missing ID for a hand-written task line (called before editing it)."""
    try:
        task = W.assign_id(body.file, body.line, body.raw)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(409, str(exc)) from exc
    return task.to_dict()


@app.post("/api/ids/repair")
def repair_ids():
    """Re-number duplicate IDs (first occurrence keeps its, the rest get new ones)."""
    try:
        return W.repair_duplicate_ids()
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(409, str(exc)) from exc


# ---------------------------------------------------------------- write


@app.post("/api/tasks", status_code=201, response_model=TaskOut)
def create_task(body: NewTaskIn):
    """Append a new task to a file; the ID is generated from today's sequence."""
    try:
        task = W.create_task(
            file=body.file, title=body.title, p=body.p, u=body.u,
            tags=body.tags, ddl=body.ddl,
        )
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(500, str(exc)) from exc
    return task.to_dict()


@app.patch("/api/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: str, body: TaskPatch):
    """Update a task: only the given fields, only the affected line."""
    given = body.model_fields_set
    if not given:
        raise HTTPException(400, "no fields to update")
    if body.title is not None and not body.title.strip():
        raise HTTPException(400, "title cannot be empty")

    try:
        if given == {"status"}:
            # Ticking: minimal rewrite, never rebuild the whole line
            if body.status is None:
                raise HTTPException(400, "status cannot be null")
            task = W.set_status(task_id, body.status)
        elif given <= {"p", "u"}:
            # Cross-cell drag: only two tokens change
            current = _task_or_404(task_id)
            new_p = body.p if body.p is not None else current.p
            new_u = body.u if body.u is not None else current.u
            if new_p is None or new_u is None:
                raise HTTPException(400, "this task is missing P or U, cannot set just one")
            task = W.set_pu(task_id, new_p, new_u)
        else:
            # Drawer edit: rebuild this line (title / tags / DDL may all change)
            changes = {key: getattr(body, key) for key in given}
            task = W.update_task(task_id, changes)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(500, str(exc)) from exc

    return task.to_dict()


@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: str):
    """Delete one task (its line plus indented detail). Irreversible: the UI asks first."""
    try:
        return W.delete_task(task_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(500, str(exc)) from exc


@app.put("/api/order")
def move_task(body: MoveIn):
    """A drag writes `.order.json` only; markdown is never touched.

    Drop semantics: move `id` immediately before/after `anchor`, using *global*
    neighbours -- so hidden tasks in between are never slipped into.
    """
    tasks = P.load_tasks()
    try:
        return order_mod.move(tasks, body.id, body.anchor, body.position)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/tasks/{task_id}/focus", response_model=TaskOut)
def add_focus(task_id: str):
    """Drop on the Focus tab: add the `#TopN` tag (idempotent)."""
    try:
        return W.add_tag(task_id, "TopN").to_dict()
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(409, str(exc)) from exc


@app.post("/api/tasks/{task_id}/someday")
def move_to_someday(task_id: str):
    """Drop on the someday tab: move the task (line + details) into 4-someday.md."""
    try:
        return W.move_to_someday(task_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(409, str(exc)) from exc


# ---------------------------------------------------------------- static files


if DIST.is_dir():
    # Production shape: the backend serves the built frontend (same origin, no CORS)
    app.mount("/", StaticFiles(directory=DIST, html=True), name="web")
else:

    @app.get("/")
    def root():
        return {
            "name": "Quadrant",
            "hint": "Frontend not built: cd web && npm run build (or npm run dev, Vite proxies /api)",
            "docs": "/docs",
            "tasksRoot": str(P.TASKS_ROOT),
        }


def _free_port(host: str, start: int, attempts: int = 40) -> int:
    """First port at or after `start` that can actually be bound.

    Windows sometimes keeps a port in LISTENING with a PID that no longer exists; a
    plain "is it in use" check is unreliable, so try binding.
    """
    import socket

    def busy(port: int) -> bool:
        # A connect probe, because on Windows SO_REUSEADDR lets bind() succeed on a
        # port another process is already listening on.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.25)
            try:
                sock.connect((host, port))
                return True
            except OSError:
                return False

    for port in range(start, start + attempts):
        if busy(port):
            continue
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((host, port))
            except OSError:
                continue
            return port
    raise SystemExit(f"no free port between {start} and {start + attempts - 1}")


if __name__ == "__main__":
    import argparse

    import uvicorn

    ap = argparse.ArgumentParser(description="Quadrant · local todo board")
    ap.add_argument("--port", type=int, default=8000, help="preferred port (auto-steps if taken)")
    ap.add_argument("--host", default="127.0.0.1", help="bind address (localhost only by default)")
    ap.add_argument("--no-reload", action="store_true", help="disable auto-reload")
    ap.add_argument("--strict-port", action="store_true", help="fail instead of trying the next port")
    args = ap.parse_args()

    port = args.port
    if not args.strict_port:
        port = _free_port(args.host, port)
        if port != args.port:
            print(f"[info] port {args.port} is busy, using {port} instead")
    print(f"[info] open http://{args.host}:{port}")

    uvicorn.run("main:app", host=args.host, port=port, reload=not args.no_reload)
