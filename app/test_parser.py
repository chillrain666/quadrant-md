"""Parsing and filtering self-tests.

Pure logic (parsing / quadrants / filtering / grouping) must be asserted.
No pytest required:

    uv run python test_parser.py

With pytest installed, `uv run pytest` works too (every function is test_*).
Everything runs in temporary directories; the real tasks/ is never touched.
"""

import tempfile
from datetime import date
from pathlib import Path

from parser import (
    KIND_SOMEDAY,
    KIND_TASK,
    P9_CELLS,
    Task,
    collect_tags,
    default_rank,
    due_bucket,
    find_suspicious,
    focus_score,
    group_of,
    is_focus,
    iter_source_files,
    load_tasks,
    make_filters,
    month_pred,
    parse_file,
    parse_task_line,
    quadrant_of,
    split_source_lines,
)

TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


# ---------------------------------------------------------------- parsing: title line


@test
def test_complete_task_line():
    got = parse_task_line("- [ ] T-261010-1 Migrate to the new auth flow #P1 #U1 #backend DDL:2026-10-15")
    assert got["id"] == "T-261010-1", got
    assert got["status"] == "todo"
    assert got["title"] == "Migrate to the new auth flow"
    assert got["p"] == 1
    assert got["u"] == 1
    assert got["tags"] == ["backend"]
    assert got["ddl"] == "2026-10-15"
    assert got["ddl_time"] is None
    assert got["done"] is None


@test
def test_done_with_completion_date():
    got = parse_task_line("- [x] T-260916-6 Pin the thread #P1 #U3 #cheatsheet DONE:2026-09-18")
    assert got["status"] == "done"
    assert got["done"] == "2026-09-18"
    assert got["title"] == "Pin the thread"
    assert got["tags"] == ["cheatsheet"]


@test
def test_blocked_status():
    got = parse_task_line("- [-] T-261010-2 Waiting for the API docs #P2 #U2")
    assert got["status"] == "blocked"
    assert got["p"] == 2 and got["u"] == 2


@test
def test_parses_without_an_id():
    got = parse_task_line("- [ ] Forgot the ID #P3 #U3")
    assert got["id"] is None
    assert got["title"] == "Forgot the ID"


@test
def test_indented_lines_are_not_tasks():
    assert parse_task_line("      - [ ] example line inside a detail") is None
    assert parse_task_line("  - [ ] indented") is None
    assert parse_task_line("") is None
    assert parse_task_line("## Study") is None


@test
def test_pu_is_case_insensitive():
    got = parse_task_line("- [ ] T-261010-3 lowercase #p2 #u3")
    assert got["p"] == 2 and got["u"] == 3
    assert got["tags"] == []


@test
def test_out_of_range_pu_is_a_plain_tag():
    got = parse_task_line("- [ ] T-261010-4 four levels? #P4 #U9")
    assert got["p"] is None and got["u"] is None
    assert got["tags"] == ["P4", "U9"]


@test
def test_tags_allow_slashes_and_cjk():
    got = parse_task_line("- [ ] T-261010-5 entry #P1 #U3 #later/someday #reading-list")
    assert got["tags"] == ["later/someday", "reading-list"]


@test
def test_tag_case_is_preserved():
    got = parse_task_line("- [ ] T-261010-6 Type along with React #P1 #U3 #React")
    assert got["tags"] == ["React"]  # no normalisation at the display layer


@test
def test_ddl_tolerates_a_time():
    got = parse_task_line("- [ ] T-261010-7 with time #P1 #U1 DDL:2026-10-15 21:00")
    assert got["ddl"] == "2026-10-15"
    assert got["ddl_time"] == "21:00"
    # The ISO "T" separator works too
    got2 = parse_task_line("- [ ] T-261010-7 with time #P1 #U1 DDL:2026-10-15T21:00")
    assert got2["ddl_time"] == "21:00"


@test
def test_block_ref_is_not_part_of_the_title():
    got = parse_task_line("- [ ] T-261010-8 Some task #P1 #U3 ^T-261010-8")
    assert got["block_ref"] == "T-261010-8"
    assert got["title"] == "Some task"
    assert "^" not in got["title"]


@test
def test_wiki_links_are_extracted():
    got = parse_task_line("- [ ] T-261010-9 Read the details of [[T-261008-3]] #P1 #U3")
    assert got["links"] == ["T-261008-3"]


@test
def test_title_keeps_markdown_bold():
    got = parse_task_line("- [ ] T-260914-2 **【priority】Prompt engineering** #P1 #U3")
    assert got["title"] == "**【priority】Prompt engineering**"


@test
def test_no_title_does_not_crash():
    got = parse_task_line("- [ ] T-261010-10 #P1 #U3")
    assert got["title"] == ""
    assert got["id"] == "T-261010-10"


# ---------------------------------------------------------------- quadrants


@test
def test_quadrant_is_p_times_u():
    assert quadrant_of(1, 1) == "Q1"
    assert quadrant_of(1, 3) == "Q2"
    assert quadrant_of(2, 1) == "Q3"
    assert quadrant_of(3, 3) == "Q4"
    assert quadrant_of(1, 2) == "Q2"  # U2 still counts as "not urgent"
    assert quadrant_of(None, 1) == "unclassified"
    assert quadrant_of(1, None) == "unclassified"


# ---------------------------------------------------------------- file parsing


def _write(path: Path, text: str, newline: str = "\n"):
    path.parent.mkdir(parents=True, exist_ok=True)
    body = text.replace("\n", newline)
    path.write_text(body, encoding="utf-8", newline="")


@test
def test_detail_belongs_to_the_task_above_verbatim():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _write(
            root / "1-active" / "study" / "study.md",
            "# Study\n\n"
            "- [ ] T-261010-1 First #P1 #U1\n"
            "      detail line one\n"
            "      detail line two\n"
            "\n"
            "- [ ] T-261010-2 Second #P1 #U3\n"
            "- [x] T-261010-3 Done already #P1 #U3 DONE:2026-10-11\n",
        )
        tasks = parse_file(root / "1-active" / "study" / "study.md", root)
        assert len(tasks) == 3, [t.id for t in tasks]
        assert tasks[0].detail == ["      detail line one", "      detail line two"]
        assert tasks[1].detail == []  # blank lines are not detail
        assert tasks[0].line == 3  # 1-based line number
        assert tasks[2].status == "done"
        assert tasks[0].project == "study"
        assert tasks[0].group_path == ["1-active", "study"]
        assert tasks[0].file == "1-active/study/study.md"


@test
def test_crlf_files_parse_correctly():
    """Files may use CRLF: do not choke on it, and never leak \\r into the title."""
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        p = root / "1-active" / "study.md"
        _write(p, "- [ ] T-261010-1 Entry in CRLF #P1 #U3\n     detail\n", newline="\r\n")
        assert "\r\n" in p.read_bytes().decode("utf-8")
        tasks = parse_file(p, root)
        assert len(tasks) == 1
        assert tasks[0].title == "Entry in CRLF"
        assert tasks[0].raw == "- [ ] T-261010-1 Entry in CRLF #P1 #U3"
        assert not tasks[0].raw.endswith("\r")
        assert tasks[0].detail == ["     detail"]


# ---------------------------------------------------------------- scan scope


@test
def test_scan_scope_includes_and_excludes():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _write(root / "README.md", "# Notes\n")
        # 0-inbox / 4-someday are **not** on the board (capture box and later list)
        _write(root / "0-inbox.md", "<!-- empty -->\n")
        _write(root / "4-someday.md", "<!-- empty -->\n")
        _write(root / "1-active" / "study" / "study.md", "x\n")
        _write(root / "1-active" / "_project-template.md", "x\n")
        _write(root / "1-active" / "projects" / "demo" / "demo.md", "x\n")
        # All of these must be excluded
        _write(root / "2-notes" / "_note-template.md", "x\n")
        _write(root / "2-notes" / "T-261008-3.md", "x\n")
        _write(root / "3-log" / "2026-10-08.md", "x\n")
        _write(root / "5-archive" / "README.md", "x\n")

        got = [p.relative_to(root).as_posix() for p in iter_source_files(root, kinds=(KIND_TASK,))]
        # The board track only reads 1-active, sorted by relative path string
        assert got == [
            "1-active/projects/demo/demo.md",
            "1-active/study/study.md",
        ], got

        # The default (writes must locate anything) also scans someday
        all_paths = [p.relative_to(root).as_posix() for p in iter_source_files(root)]
        assert "4-someday.md" in all_paths, all_paths


# ---------------------------------------------------------------- order


@test
def test_default_order_is_id_order():
    a = Task(id="T-260924-10", status="todo", title="a")
    b = Task(id="T-261005-4", status="todo", title="b")
    c = Task(id="T-260924-9", status="todo", title="c")
    d = Task(id=None, status="todo", title="d")
    got = [t.title for t in sorted([a, b, c, d], key=default_rank)]
    assert got == ["c", "a", "b", "d"], got  # 9 < 10 (numeric, not lexicographic)


# ---------------------------------------------------------------- filtering


def _filters(**kw):
    base = dict(
        q=None, p=None, u=None, tag=None, status=None, project=None, dirs=None,
        due=None, include_done=False, today=date(2026, 10, 11),
    )
    base.update(kw)
    return make_filters(**base)


def _passes(task, **kw) -> bool:
    """Run the whole predicate list (do not index [0]: the order is an internal detail)."""
    return all(pred(task) for pred in _filters(**kw))


@test
def test_keyword_matches_title_and_detail():
    t = Task(id="T-261010-1", status="todo", title="Migrate the auth flow",
             detail=["Read the notes in [[T-1]] first"])
    assert _passes(t, q="auth") is True
    assert _passes(t, q="notes") is True  # detail lines match, case-insensitively
    assert _passes(t, q="no-such-word") is False


@test
def test_keyword_also_searches_tags_projects_and_ids():
    """The title may not contain the word at all; tag/project must still find it."""
    t = Task(
        id="T-261018-1",
        status="todo",
        title="Adventurer ring",
        tags=["games", "outdoors"],
        project="outdoors",
        file="1-active/life/hobby/games/outdoors.md",
        group_path=["1-active", "life", "hobby", "games"],
    )
    assert _passes(t, q="outdoors") is True  # tag + project
    assert _passes(t, q="#outdoors") is True  # leading # works too
    assert _passes(t, q="games") is True
    assert _passes(t, q="ring") is True  # title still matches
    assert _passes(t, q="t-261018") is True  # IDs are searchable, case-insensitive
    assert _passes(t, q="hobby") is True  # directory name
    assert _passes(t, q="1-active") is False  # the outer directory never matches
    assert _passes(t, q="nothing-here") is False


@test
def test_tag_filter_is_case_insensitive_and_keeps_original_case():
    t = Task(id="T-1", status="todo", title="x", tags=["React"])
    assert _passes(t, tag=["react"]) is True
    assert _passes(t, tag=["#REACT"]) is True
    assert _passes(t, tag=["vue"]) is False
    assert t.tags == ["React"]  # untouched


@test
def test_multiple_tags_are_ored():
    t = Task(id="T-1", status="todo", title="x", tags=["backend"])
    assert _passes(t, tag=["frontend", "backend"]) is True


@test
def test_default_scope_is_todo_only():
    """Default scope is todo only: done and blocked are hidden; ask explicitly to see them."""
    todo = Task(id="T-1", status="todo", title="a")
    blocked = Task(id="T-2", status="blocked", title="b")
    done = Task(id="T-3", status="done", title="c")

    assert _passes(todo) is True
    assert _passes(blocked) is False, "blocked must be hidden by default"
    assert _passes(done) is False

    # Explicit requests still work
    assert _passes(blocked, status=["blocked"]) is True
    assert _passes(blocked, include_done=True) is True
    assert _passes(done, include_done=True) is True


@test
def test_done_is_hidden_by_default():
    done = Task(id="T-1", status="done", title="x")
    todo = Task(id="T-2", status="todo", title="y")
    default = _filters()
    assert all(p(done) for p in default) is False
    assert all(p(todo) for p in default) is True
    # An explicit status wins
    assert all(p(done) for p in _filters(status=["done"])) is True
    # include_done only stops excluding; it does not mean "done only"
    assert all(p(done) for p in _filters(include_done=True)) is True


@test
def test_p_and_u_are_independent_axes():
    t = Task(id="T-1", status="todo", title="x", p=1, u=3)
    assert all(pred(t) for pred in _filters(p=[1])) is True
    assert all(pred(t) for pred in _filters(u=[1])) is False
    assert all(pred(t) for pred in _filters(p=[1], u=[3])) is True


@test
def test_due_windows():
    today = date(2026, 10, 11)
    overdue = Task(id="T-1", status="todo", title="x", ddl="2026-10-01")
    today_due = Task(id="T-2", status="todo", title="y", ddl="2026-10-11")
    week_due = Task(id="T-3", status="todo", title="z", ddl="2026-10-16")
    far = Task(id="T-4", status="todo", title="w", ddl="2026-11-20")
    noddl = Task(id="T-5", status="todo", title="v")
    for mode, expect in [
        ("overdue", {overdue.id}),
        ("today", {today_due.id}),
        ("week", {today_due.id, week_due.id}),
        ("none", {noddl.id}),
    ]:
        got = {
            t.id
            for t in [overdue, today_due, week_due, far, noddl]
            if _passes(t, due=mode, today=today)
        }
        assert got == expect, (mode, got)


@test
def test_due_buckets_are_mutually_exclusive():
    """Grouping relies on this: a task belongs to exactly one due bucket."""
    today = date(2026, 10, 11)
    cases = [
        ("2026-10-01", "overdue"),
        ("2026-10-11", "today"),
        ("2026-10-12", "week"),
        ("2026-10-17", "week"),
        ("2026-10-18", "later"),
        (None, "none"),
    ]
    for ddl, expect in cases:
        t = Task(id="T-1", status="todo", title="x", ddl=ddl)
        assert due_bucket(t, today) == expect, (ddl, due_bucket(t, today))


@test
def test_week_filter_includes_today():
    """Filtering and grouping differ on purpose: "week" is a rolling 7 days, today included."""
    today = date(2026, 10, 11)
    today_due = Task(id="T-1", status="todo", title="a", ddl="2026-10-11")
    tomorrow = Task(id="T-2", status="todo", title="b", ddl="2026-10-12")
    assert due_bucket(today_due, today) == "today"  # as a bucket it is "today"
    assert _passes(today_due, due="week", today=today) is True  # as a filter it is also this week
    assert _passes(tomorrow, due="week", today=today) is True
    assert _passes(today_due, due="today", today=today) is True


@test
def test_calendar_month_filter():
    today = date(2026, 10, 11)
    in_month = Task(id="T-1", status="todo", title="a", ddl="2026-10-31")
    other_month = Task(id="T-2", status="todo", title="b", ddl="2026-11-01")
    noddl = Task(id="T-3", status="todo", title="c")
    pred = month_pred(today)
    assert pred(in_month) is True
    assert pred(other_month) is False
    assert pred(noddl) is False


@test
def test_done_tasks_are_never_overdue():
    t = Task(id="T-1", status="done", title="x", ddl="2026-10-01")
    assert _passes(t, due="overdue", today=date(2026, 10, 11)) is False


@test
def test_multiple_conditions_are_anded():
    t = Task(id="T-1", status="todo", title="React study", p=1, u=3, tags=["React"])
    ok = _filters(q="react", p=[1], u=[3], tag=["react"])
    assert all(pred(t) for pred in ok) is True
    bad = _filters(q="react", p=[2])
    assert all(pred(t) for pred in bad) is False


# ---------------------------------------------------------------- group and tag merging


@test
def test_group_by_tag_does_not_exist():
    """Tags overlap, so grouping by them is not a mode: it must raise, not duplicate rows."""
    try:
        group_of(Task(id="T-1", status="todo", title="x"), "tag", date(2026, 10, 11))
    except ValueError:
        return
    raise AssertionError("grouping by tag must be rejected")


@test
def test_group_keys_and_sort_positions():
    today = date(2026, 10, 11)
    t = Task(id="T-1", status="todo", title="x", p=1, u=3, ddl="2026-10-01")
    t.quadrant = quadrant_of(t.p, t.u)
    assert group_of(t, "quadrant", today)[0] == "Q2"
    assert group_of(t, "p", today)[0] == "P1"
    assert group_of(t, "u", today)[0] == "U3"
    assert group_of(t, "none", today)[0] == "all"
    assert group_of(t, "status", today)[0] == "todo"
    assert group_of(t, "due", today)[0] == "overdue"  # ddl 10-01 < today 10-11
    assert group_of(t, "project", today)[0] == ""


@test
def test_tag_merge_folds_case_variants():
    tasks = [
        Task(id="T-1", status="todo", title="a", tags=["React", "backend"]),
        Task(id="T-2", status="todo", title="b", tags=["react", "frontend"]),
    ]
    tags = collect_tags(tasks)
    react = [t for t in tags if t["key"] == "react"][0]
    assert react["count"] == 2
    assert react["label"] == "React"  # first spelling wins
    assert len(tags) == 3


# ---------------------------------------------------------------- pitfalls and Focus


@test
def test_splitting_keeps_cr_and_the_line_count():
    lines = split_source_lines("a\r\nb\r\n")
    assert lines == ["a\r", "b\r"], lines
    # splitlines() would also break on \u2028, which must not happen
    assert len(split_source_lines("a\u2028b\n")) == 1


@test
def test_missing_space_lines_are_reported():
    """`- [ ]T-x` would be dropped silently; find_suspicious must report it."""
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _write(
            root / "1-active" / "study.md",
            "- [ ] T-261001-1 okay #P1 #U1\n"
            "- [ ]T-261001-2 missing space #P1 #U1\n"
            "- [y] T-261001-3 bad status #P1 #U1\n"
            "- [ ] T-261001-4 okay 2 #P1 #U1\n",
        )
        got = find_suspicious(root)
        assert [s["line"] for s in got] == [2], got
        assert len(parse_file(root / "1-active" / "study.md", root)) == 2


@test
def test_focus_selection_uses_the_topn_tag():
    assert is_focus(Task(id="T-1", status="todo", title="x", tags=["TopN"])) is True
    assert is_focus(Task(id="T-2", status="todo", title="y", tags=["topn"])) is True
    assert is_focus(Task(id="T-3", status="todo", title="z", tags=["Top1"])) is False
    assert is_focus(Task(id="T-4", status="todo", title="w")) is False


@test
def test_focus_ordering():
    today = date(2026, 10, 18)
    overdue_long = Task(id="T-1", status="todo", title="long overdue", ddl="2026-10-01", p=3, u=3)
    overdue_short = Task(id="T-2", status="todo", title="recently overdue", ddl="2026-10-17", p=3, u=3)
    due_today = Task(id="T-3", status="todo", title="due today", ddl="2026-10-18", p=3, u=3)
    p1u1 = Task(id="T-4", status="todo", title="P1U1", p=1, u=1)
    p1 = Task(id="T-5", status="todo", title="P1", p=1, u=3)
    u1 = Task(id="T-6", status="todo", title="U1", p=3, u=1)
    far = Task(id="T-7", status="todo", title="farthest", ddl="2026-12-01", p=3, u=3)
    none = Task(id="T-8", status="todo", title="no ddl", p=3, u=3)

    got = [
        t.title
        for t in sorted(
            [none, far, u1, p1, p1u1, due_today, overdue_short, overdue_long],
            key=lambda t: focus_score(t, today),
        )
    ]
    assert got == ["long overdue", "recently overdue", "due today", "P1U1", "P1", "U1", "farthest", "no ddl"], got


@test
def test_grid_has_nine_unique_cells():
    today = date(2026, 10, 18)
    sorts = []
    for p in (1, 2, 3):
        for u in (1, 2, 3):
            t = Task(id=f"T-{p}{u}", status="todo", title="x", p=p, u=u)
            key, _label, sort = group_of(t, "p9", today)
            assert key == f"P{p}U{u}", key
            sorts.append(sort)
    assert sorted(sorts) == list(range(9)), sorts  # nine cells, no gaps, no duplicates
    assert P9_CELLS == [f"P{p}U{u}" for p in (1, 2, 3) for u in (1, 2, 3)]


@test
def test_grid_puts_incomplete_tasks_in_unclassified():
    today = date(2026, 10, 18)
    for p, u in ((None, 1), (1, None), (None, None)):
        t = Task(id="T-0", status="todo", title="y", p=p, u=u)
        assert group_of(t, "p9", today) == ("PU-", "Unclassified", 9)


@test
def test_dir_filter_is_prefix_based_and_composable():
    today = date(2026, 10, 18)
    a = Task(id="T-1", status="todo", title="a",
             file="1-active/study/study.md", group_path=["1-active", "study"])
    b = Task(id="T-2", status="todo", title="b",
             file="1-active/projects/x.md", group_path=["1-active", "projects"])
    c = Task(id="T-3", status="todo", title="c", file="0-inbox.md", group_path=[])

    assert _passes(a, dirs=["1-active/study"]) is True
    assert _passes(b, dirs=["1-active/study"]) is False
    assert _passes(b, dirs=["1-active"]) is True  # a parent covers its children
    assert _passes(a, dirs=["1-active/study", "1-active/projects"]) is True  # composition is OR
    assert _passes(b, dirs=["1-active/study", "1-active/projects"]) is True
    assert _passes(c, dirs=[""]) is True  # root = files directly under tasks/
    assert _passes(a, dirs=[""]) is False


@test
def test_dir_tree_counts_match_the_filter_semantics():
    a = Task(id="T-1", status="todo", title="a",
             file="1-active/study/study.md", group_path=["1-active", "study"])
    b = Task(id="T-2", status="todo", title="b",
             file="1-active/study/AI.md", group_path=["1-active", "study"])
    c = Task(id="T-3", status="todo", title="c", file="0-inbox.md", group_path=[])
    from parser import dir_tree

    got = {x["path"]: x["count"] for x in dir_tree([a, b, c])}
    assert got == {"": 1, "1-active": 2, "1-active/study": 2}, got


# ---------------------------------------------------------------- synonyms

SYN = [["TopN", "focus"], ["outdoors", "camping"]]


@test
def test_synonyms_tag_filter_is_equivalent_and_case_insensitive():
    t1 = Task(id="T-1", status="todo", title="a", tags=["Focus"])
    t2 = Task(id="T-2", status="todo", title="b", tags=["outdoors"])
    assert _passes(t1, tag=["topn"], groups=SYN) is True
    assert _passes(t1, tag=["#TOPN"], groups=SYN) is True
    assert _passes(t2, tag=["camping"], groups=SYN) is True
    assert _passes(t2, tag=["outdoors"], groups=SYN) is True
    # Groups never leak into each other
    assert _passes(t1, tag=["outdoors"], groups=SYN) is False


@test
def test_synonyms_expand_search_both_ways():
    t = Task(
        id="T-1", status="todo", title="camping trip",
        tags=["camping"], project="outdoors",
        file="1-active/camping.md", group_path=["1-active"],
    )
    assert _passes(t, q="outdoors", groups=SYN) is True
    assert _passes(t, q="camping", groups=SYN) is True
    assert _passes(t, q="CAMPING", groups=SYN) is True

    focus = Task(id="T-2", status="todo", title="write the weekly", tags=["focus"])
    assert _passes(focus, q="TopN", groups=SYN) is True
    assert _passes(focus, q="topn", groups=SYN) is True


@test
def test_synonyms_focus_accepts_the_alias():
    a = Task(id="T-1", status="todo", title="a", tags=["focus"])
    b = Task(id="T-2", status="todo", title="b", tags=["TopN"])
    c = Task(id="T-3", status="todo", title="c", tags=["Top1"])
    assert is_focus(a, SYN) is True
    assert is_focus(b, SYN) is True
    assert is_focus(c, SYN) is False


@test
def test_synonyms_tag_list_merges_and_picks_the_most_frequent_spelling():
    tasks = [
        Task(id="T-1", status="todo", title="a", tags=["TopN"]),
        Task(id="T-2", status="todo", title="b", tags=["TopN"]),
        Task(id="T-3", status="todo", title="c", tags=["focus"]),
        Task(id="T-4", status="todo", title="d", tags=["camping"]),
    ]
    got = {t["key"]: t for t in collect_tags(tasks, SYN)}
    assert got["topn"]["count"] == 3
    assert got["topn"]["label"] == "TopN"  # the most frequent spelling
    assert got["outdoors"]["count"] == 1
    assert got["outdoors"]["label"] == "camping"


@test
def test_synonyms_group_may_hold_more_than_two_terms():
    groups = [["a", "b", "c"]]
    t = Task(id="T-1", status="todo", title="x", tags=["C"])
    assert _passes(t, tag=["a"], groups=groups) is True
    assert _passes(t, q="b", groups=groups) is True


@test
def test_synonyms_empty_table_degrades_gracefully():
    t = Task(id="T-1", status="todo", title="x", tags=["camping"])
    assert _passes(t, tag=["outdoors"], groups=[]) is False
    assert _passes(t, tag=["CAMPING"], groups=[]) is True  # only case-insensitivity is left


@test
def test_someday_accepts_both_entry_kinds():
    """someday holds task lines with an ID and free bullets without one."""
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _write(
            root / "4-someday.md",
            "# 4-someday\n\n"
            "- YYYY-MM-DD — <one line>\n\n"          # template line, must be skipped
            "- 2026-10-20 — an idea\n"
            "      detail one\n"
            "      detail two\n\n"
            "- [ ] T-261020-1 With an ID #P1 #U3\n",
        )
        items = parse_file(root / "4-someday.md", root)
        assert len(items) == 2, [t.title for t in items]
        assert items[0].id is None
        assert items[0].title == "2026-10-20 — an idea"
        assert items[0].detail == ["      detail one", "      detail two"]
        assert items[0].kind == KIND_SOMEDAY
        assert items[1].id == "T-261020-1"
        assert items[1].p == 1 and items[1].u == 3
        assert items[1].kind == KIND_SOMEDAY


@test
def test_someday_is_not_scanned_by_the_board_track():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _write(root / "4-someday.md", "- 2026-10-20 — some idea\n")
        _write(root / "1-active" / "x.md", "- [ ] T-261020-2 Normal task #P1 #U3\n")
        board = load_tasks(root, kinds=(KIND_TASK,))
        assert [t.title for t in board] == ["Normal task"]
        someday = load_tasks(root, kinds=(KIND_SOMEDAY,))
        assert [t.title for t in someday] == ["2026-10-20 — some idea"]


# ---------------------------------------------------------------- panel order


@test
def test_panel_order_follows_the_list_and_keeps_others_at_the_end():
    import lists as L

    a = Task(id="T-1", status="todo", title="a", raw="- a")
    b = Task(id="T-2", status="todo", title="b", raw="- b")
    c = Task(id=None, status="todo", title="c", raw="- c")

    got = L.sort_by([a, b, c], ["T-2", "- c"])
    assert [t.id or t.raw for t in got] == ["T-2", "- c", "T-1"]

    # An empty list changes nothing
    assert [t.id or t.raw for t in L.sort_by([a, b, c], [])] == ["T-1", "T-2", "- c"]


@test
def test_panel_order_round_trips():
    import lists as L

    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / ".lists.json"
        L.save("focus", ["T-9", "T-8"], path=p)
        L.save("someday", ["- some idea"], path=p)
        got = L.load(p)
        assert got == {"focus": ["T-9", "T-8"], "someday": ["- some idea"]}, got


@test
def test_duplicate_ids_are_reported():
    from parser import find_duplicate_ids

    tasks = [
        Task(id="T-1", status="todo", title="a", file="x.md", line=3),
        Task(id="T-1", status="todo", title="b", file="y.md", line=5),
        Task(id="T-2", status="todo", title="c", file="x.md", line=9),
    ]
    got = find_duplicate_ids(tasks)
    assert len(got) == 1, got
    assert got[0]["id"] == "T-1" and got[0]["count"] == 2
    assert got[0]["occurrences"][0] == {"file": "x.md", "line": 3, "title": "a"}


@test
def test_keyword_pred_is_usable_alone():
    from parser import keyword_pred

    t = Task(id="T-1", status="todo", title="Auth migration", tags=["backend"])
    assert keyword_pred("auth")(t) is True
    assert keyword_pred("#backend")(t) is True
    assert keyword_pred("nope")(t) is False


# ---------------------------------------------------------------- run


@test
def test_follow_dir_is_the_follow_track():
    """`follow/` is the second track: kind=follow, never mixed into the board."""
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _write(root / "1-active" / "study.md", "- [ ] T-261020-1 On the board #P1 #U3\n")
        _write(root / "follow" / "shows.md", "- [ ] T-261020-2 Follow Silicon Valley #shows\n")

        allt = load_tasks(root)
        assert len(allt) == 2, [t.id for t in allt]
        kinds = {t.project: t.kind for t in allt}
        assert kinds["study"] == "task", kinds
        assert kinds["shows"] == "follow", kinds

        only = load_tasks(root, kinds=("task",))
        assert [t.project for t in only] == ["study"], only

        assert len(iter_source_files(root, kinds=("task",))) == 1
        assert len(iter_source_files(root, kinds=("follow",))) == 1


@test
def test_follow_entries_need_no_p_or_u():
    """Follow lists have no quadrants: missing P/U is not an error and stays off the board."""
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _write(root / "follow" / "books.md", "- [ ] T-261020-3 Untitled (TBD) #books\n")
        t = load_tasks(root, kinds=("follow",))[0]
        assert t.p is None and t.u is None, t
        assert t.kind == "follow"
        assert t.tags == ["books"], t.tags
        assert load_tasks(root, kinds=("task",)) == []


if __name__ == "__main__":
    failed = []
    for fn in TESTS:
        try:
            fn()
            print(f"  ok   {fn.__name__}")
        except Exception as exc:  # noqa: BLE001 - make it obvious which one broke
            failed.append(fn.__name__)
            print(f"  FAIL {fn.__name__}: {type(exc).__name__}: {exc}")

    print(f"\n{len(TESTS) - len(failed)}/{len(TESTS)} passed")
    if failed:
        print("failed:", ", ".join(failed))
    raise SystemExit(1 if failed else 0)
