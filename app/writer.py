"""Write-back layer: turn UI actions into markdown edits.

Iron rule: **touch only the line you meant to touch**.
- line order, other lines, indented details and newline style are never touched
- newline style is **preserved per file** (a data directory may mix LF and CRLF)
- the original bytes are kept before writing; after writing the file is parsed
  again and verified, and **restored** if verification fails
"""

from __future__ import annotations

import os
import re
import threading
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from parser import (
    TASKS_ROOT,
    Task,
    find_duplicate_ids,
    iter_source_files,
    parse_file,
    parse_task_line,
    split_source_lines,
)

WRITE_LOCK = threading.Lock()

STATUS_MARK = {"todo": " ", "done": "x", "blocked": "-"}

CHECKBOX_RE = re.compile(r"^- \[([ xX-])\]")
# A leading whitespace is required so removing DONE never leaves a double space
REMOVE_DONE_RE = re.compile(r"[ \t]+DONE:\d{4}-\d{2}-\d{2}\b")
BLOCK_TAIL_RE = re.compile(r"[ \t]+\^T-\d{6}-\d+[ \t]*$")
# P/U tags must be followed by whitespace or end of line, so #P1-x is not
# matched by accident
P_TAG_RE = re.compile(r"#P\d(?=\s|$)")
U_TAG_RE = re.compile(r"#U\d(?=\s|$)")
BOM = b"\xef\xbb\xbf"
# The ID is the first token after the checkbox; only that token is rewritten.
ID_IN_LINE_RE = re.compile(r"^(\s*- \[[ xX-]\]\s+)(T-\d{6}-\d+)(?=\s|$)")


# ---------------------------------------------------------------- file I/O


@dataclass
class Source:
    path: Path
    lines: list[str]  # each line **keeps its trailing \r** (CRLF files)
    had_bom: bool
    newline: str  # "\r\n" or "\n", used for appended lines
    ends_with_newline: bool


def read_source(path: Path) -> Source:
    data = path.read_bytes()
    had_bom = data.startswith(BOM)
    if had_bom:
        data = data[len(BOM) :]
    # No universal-newline translation: we want the bytes as they are
    text = data.decode("utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    ends_with_newline = text.endswith("\n")
    return Source(
        path=path,
        lines=split_source_lines(text),
        had_bom=had_bom,
        newline=newline,
        ends_with_newline=ends_with_newline,
    )


def render_source(src: Source) -> bytes:
    text = "\n".join(src.lines)
    if src.ends_with_newline:
        text += "\n"
    data = text.encode("utf-8")
    return BOM + data if src.had_bom else data


def new_line_text(src: Source, body: str) -> str:
    """Append the file's own line ending to a new line body (`\\r` pairs with the
    `\\n` added on join)."""
    return body + ("\r" if src.newline == "\r\n" else "")


def _atomic_write(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


# ---------------------------------------------------------------- locating


def locate(root: Path, task_id: str) -> tuple[Task, Path]:
    """Locate the file containing a task by ID. IDs, not line numbers: line numbers drift."""
    hits: list[tuple[Task, Path]] = []
    for path in iter_source_files(root):
        for task in parse_file(path, root):
            if task.id == task_id:
                hits.append((task, path))
    if not hits:
        raise LookupError(f"task not found: {task_id}")
    if len(hits) > 1:
        # Duplicate IDs are a bug to fix. Refuse to guess instead of editing both.
        files = ", ".join(p.relative_to(root).as_posix() for _, p in hits)
        raise ValueError(f"duplicate ID {task_id} found in: {files}")
    return hits[0]


def _resolve_inside(root: Path, file: str) -> Path:
    """Resolve `file` under `root` and refuse anything that escapes it."""
    rootr = root.resolve()
    path = (root / file).resolve()
    if rootr not in path.parents and path.parent != rootr:
        raise ValueError("the target file must live inside the tasks directory")
    if not path.is_file():
        raise LookupError(f"file not found: {file}")
    return path


def assign_id(
    file: str,
    line: int,
    raw: str,
    *,
    root: Path = TASKS_ROOT,
    today: date | None = None,
) -> Task:
    """Give an ID to a task line that has none, in place.

    Hand-written tasks do not need an ID up front: the first time the UI wants to
    edit one, it calls this and the ID is filled in. Locating is done by
    file + line + exact text, so a concurrently edited file is refused rather than
    corrupted. Returns the parsed task (with its ID).
    """
    with WRITE_LOCK:
        root = root.resolve()
        path = _resolve_inside(root, file)
        src = read_source(path)
        original = path.read_bytes()

        if not 1 <= line <= len(src.lines):
            raise ValueError(f"line out of range: {line}")
        body = _line_body(src, line)
        if body.strip() != str(raw).strip():
            raise RuntimeError("the line no longer matches (edited by hand?), aborted")

        parsed = parse_task_line(body)
        if parsed is None:
            raise ValueError(f"not a task line: {body!r}")
        if parsed["id"]:
            found = [t for t in parse_file(path, root) if t.line == line]
            if len(found) == 1:
                return found[0]

        m = CHECKBOX_RE.match(body)
        if not m:
            raise ValueError(f"not a task line: {body!r}")
        new_id = next_id(root, today)
        _set_line(src, line, body[: m.end()] + " " + new_id + body[m.end() :])
        _atomic_write(path, render_source(src))

        try:
            found = [t for t in parse_file(path, root) if t.line == line]
            if len(found) != 1 or found[0].id != new_id:
                raise RuntimeError(f"post-write check failed for {new_id}")
            return found[0]
        except Exception:
            _atomic_write(path, original)
            raise


def repair_duplicate_ids(
    *, root: Path = TASKS_ROOT, today: date | None = None
) -> dict:
    """Re-number duplicate IDs: the first occurrence keeps its ID, the rest get new ones.

    Only the ID token is rewritten on the affected lines; every other byte stays.
    All files are restored if the post-write verification finds a problem.
    """
    today = today or date.today()
    ymd = today.strftime("%y%m%d")

    with WRITE_LOCK:
        root = root.resolve()
        files = iter_source_files(root)
        tasks: list[Task] = []
        for path in files:
            tasks.extend(parse_file(path, root))
        tasks.sort(key=lambda t: (t.file, t.line))

        seq = int(next_id(root, today).rsplit("-", 1)[1])
        seen: set[str] = set()
        plan: dict[Path, dict[int, str]] = {}
        renamed: list[dict] = []

        for t in tasks:
            if not t.id:
                continue
            if t.id not in seen:
                seen.add(t.id)
                continue
            while True:
                candidate = f"T-{ymd}-{seq}"
                seq += 1
                if candidate not in seen:
                    break
            seen.add(candidate)
            plan.setdefault(root / t.file, {})[t.line] = candidate
            renamed.append(
                {"file": t.file, "line": t.line, "from": t.id, "to": candidate}
            )

        if not renamed:
            return {"changed": 0, "renamed": [], "remaining": []}

        originals: dict[Path, bytes] = {}
        try:
            for path, line_map in plan.items():
                src = read_source(path)
                originals[path] = path.read_bytes()
                for lineno, new_id in line_map.items():
                    body = _line_body(src, lineno)
                    new_body, hits = ID_IN_LINE_RE.subn(
                        lambda m: m.group(1) + new_id, body, count=1
                    )
                    if hits != 1:
                        raise RuntimeError(
                            f"could not rewrite the ID on {path.name}:{lineno}"
                        )
                    _set_line(src, lineno, new_body)
                _atomic_write(path, render_source(src))

            after: list[Task] = []
            for path in files:
                after.extend(parse_file(path, root))
            left = find_duplicate_ids(after)
            if left or len(after) != len(tasks):
                raise RuntimeError("duplicate IDs are still present after the repair")
        except Exception:
            for path, data in originals.items():
                _atomic_write(path, data)
            raise

        return {"changed": len(renamed), "renamed": renamed, "remaining": []}


def _line_body(src: Source, lineno: int) -> str:
    raw = src.lines[lineno - 1]
    return raw[:-1] if raw.endswith("\r") else raw


def _set_line(src: Source, lineno: int, body: str) -> None:
    old = src.lines[lineno - 1]
    src.lines[lineno - 1] = body + ("\r" if old.endswith("\r") else "")


# ---------------------------------------------------------------- status changes


def rebuild_status_line(body: str, status: str, today: date) -> str:
    """Change only the checkbox and the DONE marker; everything else stays byte-identical."""
    m = CHECKBOX_RE.match(body)
    if not m:
        raise ValueError(f"not a task line: {body!r}")

    line = f"- [{STATUS_MARK[status]}]" + body[m.end() :]
    line = REMOVE_DONE_RE.sub("", line)  # drop the old DONE first

    if status == "done":
        done = f"DONE:{today.isoformat()}"
        tail = BLOCK_TAIL_RE.search(line)
        if tail:  # insert before a trailing ^T-xxx block reference
            line = line[: tail.start()] + " " + done + line[tail.start() :]
        else:
            line = line.rstrip() + " " + done
    return line


def set_status(
    task_id: str,
    status: str,
    *,
    root: Path = TASKS_ROOT,
    today: date | None = None,
) -> Task:
    """Switch status: todo / done (stamps the DONE date) / blocked."""
    if status not in STATUS_MARK:
        raise ValueError("status must be one of: todo / done / blocked")
    today = today or date.today()

    with WRITE_LOCK:
        task, path = locate(root, task_id)
        src = read_source(path)
        original = path.read_bytes()

        body = _line_body(src, task.line)
        if task_id not in body:
            raise RuntimeError("the line no longer matches the parse result (edited by hand?), aborted")

        _set_line(src, task.line, rebuild_status_line(body, status, today))
        _atomic_write(path, render_source(src))

        try:
            return _verify(root, task_id, path, expected_status=status)
        except Exception:
            _atomic_write(path, original)  # restore on failed verification
            raise


# ---------------------------------------------------------------- P/U changes


def rebuild_pu_line(body: str, p: int, u: int) -> str:
    """Replace only the `#P{n}` / `#U{n}` tokens; every other byte stays.

    Existing tags are replaced **in place** (order and position preserved); a
    missing one is appended before any trailing block reference.
    """
    line = body
    has_p = P_TAG_RE.search(line) is not None
    has_u = U_TAG_RE.search(line) is not None
    if has_p:
        line = P_TAG_RE.sub(f"#P{p}", line, count=1)
    if has_u:
        line = U_TAG_RE.sub(f"#U{u}", line, count=1)

    missing = [tag for tag, had in ((f"#P{p}", has_p), (f"#U{u}", has_u)) if not had]
    if missing:
        insert = " ".join(missing)
        tail = BLOCK_TAIL_RE.search(line)
        if tail:
            line = line[: tail.start()] + " " + insert + line[tail.start() :]
        else:
            line = line.rstrip() + " " + insert
    return line


def set_pu(
    task_id: str,
    p: int,
    u: int,
    *,
    root: Path = TASKS_ROOT,
) -> Task:
    """Change importance/urgency (this is what cross-cell drags call)."""
    if p not in (1, 2, 3) or u not in (1, 2, 3):
        raise ValueError("p / u must be 1, 2 or 3")

    with WRITE_LOCK:
        task, path = locate(root, task_id)
        src = read_source(path)
        original = path.read_bytes()

        body = _line_body(src, task.line)
        if task_id not in body:
            raise RuntimeError("the line no longer matches the parse result (edited by hand?), aborted")

        _set_line(src, task.line, rebuild_pu_line(body, p, u))
        _atomic_write(path, render_source(src))

        try:
            return _verify(root, task_id, path, expected_p=p, expected_u=u)
        except Exception:
            _atomic_write(path, original)  # restore on failed verification
            raise


# ---------------------------------------------------------------- whole-line rewrite

_UNSET = object()


def rebuild_line(
    *,
    task_id: str | None,
    status: str,
    title: str,
    p: int | None,
    u: int | None,
    tags: list[str],
    ddl: str | None,
    done: str | None,
    block_ref: str | None,
) -> str:
    """Rebuild a task line. Field order matches the on-disk convention:
    ID -> title -> #P -> #U -> tags -> DDL -> DONE -> ^block-ref."""
    parts = [f"- [{STATUS_MARK[status]}]"]
    if task_id:
        parts.append(task_id)
    if title.strip():
        parts.append(title.strip())
    if p:
        parts.append(f"#P{p}")
    if u:
        parts.append(f"#U{u}")
    for tag in tags:
        clean = str(tag).strip().lstrip("#").strip()
        if clean:
            parts.append(f"#{clean}")
    if ddl:
        parts.append(f"DDL:{ddl}")
    if done:
        parts.append(f"DONE:{done}")
    line = " ".join(parts)
    if block_ref:
        line += f" ^{block_ref}"
    return line


def update_task(
    task_id: str,
    changes: dict,
    *,
    root: Path = TASKS_ROOT,
    today: date | None = None,
) -> Task:
    """Update one task by field (title / P / U / tags / DDL / status).

    Every key present in `changes` is applied; `ddl=None` clears the due date.
    Only **this one line** is rewritten: line order, detail lines and newlines
    stay untouched. The file is re-parsed afterwards and restored on mismatch.
    """
    if "title" in changes:
        title = str(changes["title"] or "").strip()
        if not title:
            raise ValueError("title cannot be empty")
    for key in ("p", "u"):
        if key in changes and changes[key] is not None and changes[key] not in (1, 2, 3):
            raise ValueError(f"{key} must be 1, 2 or 3")
    if "ddl" in changes and changes["ddl"] is not None:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(changes["ddl"])):
            raise ValueError("DDL must look like YYYY-MM-DD")
    if "status" in changes and changes["status"] not in STATUS_MARK:
        raise ValueError("status must be one of: todo / done / blocked")
    if "tags" in changes:
        # Normalise at the entry point (strip #, drop blanks) so the rebuild and
        # the verification work on the same values
        changes["tags"] = [
            clean
            for clean in (str(t).strip().lstrip("#").strip() for t in (changes["tags"] or []))
            if clean
        ]

    with WRITE_LOCK:
        task, path = locate(root, task_id)
        src = read_source(path)
        original = path.read_bytes()

        body = _line_body(src, task.line)
        if task_id not in body:
            raise RuntimeError("the line no longer matches the parse result (edited by hand?), aborted")

        status = changes.get("status", task.status)
        done = task.done
        if status != "done":
            done = None
        elif changes.get("status") == "done" and not task.done:
            done = (today or date.today()).isoformat()

        new_line = rebuild_line(
            task_id=task.id,
            status=status,
            title=changes.get("title", task.title),
            p=changes.get("p", task.p),
            u=changes.get("u", task.u),
            tags=changes.get("tags", task.tags),
            ddl=changes.get("ddl", task.ddl),
            done=done,
            block_ref=task.block_ref,
        )
        _set_line(src, task.line, new_line)
        _atomic_write(path, render_source(src))

        try:
            return _verify(
                root,
                task_id,
                path,
                expected_status=status,
                expected_p=changes.get("p", _UNSET),
                expected_u=changes.get("u", _UNSET),
                expected_title=changes.get("title").strip() if "title" in changes else _UNSET,
                expected_ddl=changes.get("ddl", _UNSET),
                expected_tags=changes.get("tags", _UNSET),
            )
        except Exception:
            _atomic_write(path, original)
            raise


# ---------------------------------------------------------------- tags / tracks


def add_tag(task_id: str, tag: str, *, root: Path = TASKS_ROOT) -> Task:
    """Add one tag to a task (idempotent, case-insensitive). Used by dropping on Focus."""
    task, _ = locate(root.resolve(), task_id)
    clean = str(tag).strip().lstrip("#").strip()
    if not clean:
        raise ValueError("tag cannot be empty")
    tags = list(task.tags)
    if clean.lower() not in {t.lower() for t in tags}:
        tags.append(clean)
    return update_task(task_id, {"tags": tags}, root=root)


def move_to_someday(
    task_id: str, *, root: Path = TASKS_ROOT, target: str = "4-someday.md"
) -> dict:
    """Move a task (line + indented details) out of its file into `4-someday.md`.

    The ID does not change: it is identity, not location. Both files are restored if
    the post-write verification fails.
    """
    with WRITE_LOCK:
        root = root.resolve()
        task, source = locate(root, task_id)
        destination = root / target
        if not destination.is_file():
            raise LookupError(f"file not found: {target}")

        src = read_source(source)
        dst = read_source(destination)
        src_bytes = source.read_bytes()
        dst_bytes = destination.read_bytes()

        start = task.line - 1
        end = start + 1
        while end < len(src.lines):
            body = src.lines[end]
            body = body[:-1] if body.endswith("\r") else body
            if body[:1] in (" ", "\t") and body.strip():
                end += 1
                continue
            break

        block = src.lines[start:end]
        moved = len(block)
        del src.lines[start:end]

        # Keep the destination's newline style; drop an extra blank line at EOF.
        while dst.lines and not dst.lines[-1].strip():
            dst.lines.pop()
        if dst.lines:
            dst.lines.append(new_line_text(dst, ""))
        for line in block:
            body = line[:-1] if line.endswith("\r") else line
            dst.lines.append(new_line_text(dst, body))
        dst.ends_with_newline = True

        _atomic_write(source, render_source(src))
        _atomic_write(destination, render_source(dst))

        try:
            if [t for t in parse_file(source, root) if t.id == task_id]:
                raise RuntimeError(f"{task_id} is still in {source.name}")
            landed = [t for t in parse_file(destination, root) if t.id == task_id]
            if len(landed) != 1:
                raise RuntimeError(f"{task_id} did not land in {target}")
        except Exception:
            _atomic_write(source, src_bytes)
            _atomic_write(destination, dst_bytes)
            raise

        return {
            "id": task_id,
            "from": source.relative_to(root).as_posix(),
            "to": target,
            "movedLines": moved,
        }


# ---------------------------------------------------------------- create


def next_id(root: Path = TASKS_ROOT, today: date | None = None) -> str:
    """Next ID for today: max daily sequence across the whole tree (notes and logs
    included) plus one."""
    today = today or date.today()
    ymd = today.strftime("%y%m%d")
    pattern = re.compile(rf"T-{ymd}-(\d+)")
    max_seq = 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in {".git", ".obsidian", ".venv"} for part in rel.parts):
            continue
        if path.suffix not in {".md", ".txt"}:
            continue
        try:
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
        except OSError:
            continue
        for m in pattern.finditer(text):
            max_seq = max(max_seq, int(m.group(1)))
    return f"T-{ymd}-{max_seq + 1}"


def build_task_line(
    task_id: str,
    title: str,
    p: int | None = None,
    u: int | None = None,
    tags: list[str] | None = None,
    ddl: str | None = None,
) -> str:
    """Build a new task line in the documented format:

    `- [ ] {ID} {title} #P1 #U3 #tag DDL:YYYY-MM-DD`
    """
    parts = [f"- [ ] {task_id}", title.strip()]
    if p:
        parts.append(f"#P{p}")
    if u:
        parts.append(f"#U{u}")
    for tag in tags or []:
        clean = tag.strip().lstrip("#").strip()
        if clean:
            parts.append(f"#{clean}")
    if ddl:
        parts.append(f"DDL:{ddl}")
    return " ".join(parts)


def create_task(
    *,
    file: str,
    title: str,
    p: int | None = None,
    u: int | None = None,
    tags: list[str] | None = None,
    ddl: str | None = None,
    root: Path = TASKS_ROOT,
    today: date | None = None,
) -> Task:
    """Append a task to the **end** of a file and return the parsed result."""
    today = today or date.today()
    title = (title or "").strip()
    if not title:
        raise ValueError("title cannot be empty")

    path = (root / file).resolve()
    if root.resolve() not in path.parents and path.parent != root.resolve():
        raise ValueError("the target file must live inside the tasks directory")
    if not path.is_file():
        raise LookupError(f"file not found: {file}")
    if path.name.startswith("_") or path.name == "README.md":
        raise ValueError("cannot add tasks to a template or README file")

    with WRITE_LOCK:
        task_id = next_id(root, today)
        body = build_task_line(task_id, title, p, u, tags, ddl)

        src = read_source(path)
        original = path.read_bytes()

        src.lines.append(new_line_text(src, body))
        src.ends_with_newline = True
        _atomic_write(path, render_source(src))

        try:
            return _verify(root, task_id, path, expected_status="todo")
        except Exception:
            _atomic_write(path, original)
            raise


# ---------------------------------------------------------------- delete


def delete_task(task_id: str, *, root: Path = TASKS_ROOT) -> dict:
    """Delete one task (**its line plus its indented detail lines**); nothing else changes.

    After deleting, the file is re-parsed: the ID must be gone, otherwise the
    original bytes are restored. This really deletes: keep the data directory
    under git if you want an undo.
    """
    with WRITE_LOCK:
        task, path = locate(root, task_id)
        src = read_source(path)
        original = path.read_bytes()

        start = task.line - 1
        end = start + 1
        # Indented non-empty lines right below belong to this task: remove them too
        while end < len(src.lines):
            body = src.lines[end]
            body = body[:-1] if body.endswith("\r") else body
            if body[:1] in (" ", "\t") and body.strip():
                end += 1
                continue
            break

        removed = src.lines[start:end]
        del src.lines[start:end]
        _atomic_write(path, render_source(src))

        try:
            left = [t for t in parse_file(path, root) if t.id == task_id]
            if left:
                raise RuntimeError(f"{task_id} is still parseable after deletion")
        except Exception:
            _atomic_write(path, original)
            raise

        return {
            "id": task_id,
            "file": path.relative_to(root).as_posix(),
            "title": task.title,
            "removedLines": len(removed),
            "removedRaw": removed[0].rstrip("\r") if removed else "",
        }


# ---------------------------------------------------------------- verification


def _verify(
    root: Path,
    task_id: str,
    path: Path,
    *,
    expected_status: str | None = None,
    expected_p: object = _UNSET,
    expected_u: object = _UNSET,
    expected_title: object = _UNSET,
    expected_ddl: object = _UNSET,
    expected_tags: object = _UNSET,
) -> Task:
    """Re-parse after writing and confirm: the task exists, the changed fields are
    correct and the ID is not duplicated.

    `_UNSET` distinguishes "not passed" from "explicitly set to None" (clearing
    a DDL, for example).
    """
    tasks = parse_file(path, root)
    found = [t for t in tasks if t.id == task_id]
    if len(found) != 1:
        raise RuntimeError(f"post-write check failed: {task_id} appears {len(found)} times")
    task = found[0]

    if expected_status is not None and task.status != expected_status:
        raise RuntimeError(f"post-write check failed: status is {task.status}, expected {expected_status}")

    checks = (
        ("P", expected_p, task.p),
        ("U", expected_u, task.u),
        ("title", expected_title, task.title),
        ("DDL", expected_ddl, task.ddl),
        ("tags", expected_tags, task.tags),
    )
    for name, expected, actual in checks:
        if expected is not _UNSET and expected != actual:
            raise RuntimeError(f"post-write check failed: {name} is {actual!r}, expected {expected!r}")
    return task
