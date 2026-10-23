"""Self-tests for writer.py -- this code mutates data, so no assertion can be skipped.

Everything runs against temporary directories; the real tasks/ is never touched.
Run: uv run python test_writer.py
"""

import tempfile
from datetime import date
from pathlib import Path

import parser as P
import writer as W

TESTS = []
TODAY = date(2026, 10, 18)


def test(fn):
    TESTS.append(fn)
    return fn


def write(path: Path, text: str, newline: str = "\n", bom: bool = False) -> None:
    """Create a file with the requested newline/BOM (real bytes, no translation)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = text.replace("\n", newline).encode("utf-8")
    path.write_bytes((b"\xef\xbb\xbf" if bom else b"") + data)


SAMPLE = (
    "# Study\n"
    "\n"
    "- [ ] T-261001-1 First task #P1 #U1\n"
    "      detail line one\n"
    "      detail line two\n"
    "\n"
    "- [ ] T-261001-2 Second task #P1 #U3 DDL:2026-10-20\n"
)


# ---------------------------------------------------------------- status changes


@test
def test_completing_touches_only_that_line():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        f = root / "1-active" / "study" / "study.md"
        write(f, SAMPLE, newline="\r\n")
        before = f.read_bytes()

        task = W.set_status("T-261001-1", "done", root=root, today=TODAY)

        after = f.read_bytes()
        assert task.status == "done"
        assert task.done == "2026-10-18"

        old_lines = before.decode("utf-8").split("\n")
        new_lines = after.decode("utf-8").split("\n")
        assert len(old_lines) == len(new_lines), "the line count must not change"
        changed = [i for i, (a, b) in enumerate(zip(old_lines, new_lines)) if a != b]
        assert changed == [2], f"only line 3 (index 2) should change, got {changed}"
        assert new_lines[2] == "- [x] T-261001-1 First task #P1 #U1 DONE:2026-10-18\r"


@test
def test_crlf_and_lf_are_preserved_per_file():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        crlf = root / "1-active" / "a.md"
        lf = root / "1-active" / "b.md"
        write(crlf, SAMPLE, newline="\r\n")
        write(lf, SAMPLE.replace("T-261001-", "T-261002-"), newline="\n")

        W.set_status("T-261001-1", "done", root=root, today=TODAY)
        crlf_bytes = crlf.read_bytes()
        lf_bytes = lf.read_bytes()
        assert crlf_bytes.count(b"\r\n") == 7, crlf_bytes
        assert crlf_bytes.count(b"\n") - crlf_bytes.count(b"\r\n") == 0
        assert lf_bytes.count(b"\r\n") == 0, lf_bytes


@test
def test_unticking_removes_done_without_double_spaces():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        f = root / "1-active" / "study.md"
        write(f, SAMPLE)
        W.set_status("T-261001-1", "done", root=root, today=TODAY)
        task = W.set_status("T-261001-1", "todo", root=root, today=TODAY)

        raw = f.read_text(encoding="utf-8").splitlines()[2]
        assert task.status == "todo"
        assert task.done is None
        assert "DONE:" not in raw
        assert "  " not in raw, f"no double spaces allowed: {raw!r}"
        assert raw == "- [ ] T-261001-1 First task #P1 #U1"


@test
def test_blocked_status():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        f = root / "1-active" / "study.md"
        write(f, SAMPLE)
        task = W.set_status("T-261001-1", "blocked", root=root, today=TODAY)
        assert task.status == "blocked"
        assert f.read_text(encoding="utf-8").splitlines()[2].startswith("- [-] T-261001-1")


@test
def test_done_goes_before_a_block_reference():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        f = root / "1-active" / "study.md"
        write(f, "- [ ] T-261001-9 With block ref #P1 #U1 ^T-261001-9\n")
        W.set_status("T-261001-9", "done", root=root, today=TODAY)
        raw = f.read_text(encoding="utf-8").strip()
        assert raw == "- [x] T-261001-9 With block ref #P1 #U1 DONE:2026-10-18 ^T-261001-9", raw


@test
def test_detail_lines_and_other_tasks_stay_byte_identical():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        f = root / "1-active" / "study.md"
        write(f, SAMPLE)
        before = [ln for i, ln in enumerate(f.read_text(encoding="utf-8").split("\n")) if i != 2]
        W.set_status("T-261001-1", "done", root=root, today=TODAY)
        after = [ln for i, ln in enumerate(f.read_text(encoding="utf-8").split("\n")) if i != 2]
        assert before == after


# ---------------------------------------------------------------- P/U changes


@test
def test_p_and_u_change_only_those_tokens():
    body = "- [ ] T-261001-1 First task #P1 #U1 #backend DDL:2026-10-20"
    assert W.rebuild_pu_line(body, 2, 2) == "- [ ] T-261001-1 First task #P2 #U2 #backend DDL:2026-10-20"


@test
def test_missing_tags_are_appended_at_the_end():
    body = "- [ ] T-261001-1 No priority yet"
    assert W.rebuild_pu_line(body, 2, 3) == "- [ ] T-261001-1 No priority yet #P2 #U3"


@test
def test_missing_tags_are_inserted_before_the_block_ref():
    body = "- [ ] T-261001-1 Something ^T-261001-1"
    assert W.rebuild_pu_line(body, 1, 2) == "- [ ] T-261001-1 Something #P1 #U2 ^T-261001-1"


@test
def test_lookalike_tags_are_not_touched():
    body = "- [ ] T-261001-1 Title #P1x #P1"
    assert W.rebuild_pu_line(body, 2, 1) == "- [ ] T-261001-1 Title #P1x #P2 #U1"


@test
def test_cross_quadrant_move_touches_one_line_and_keeps_crlf():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        f = root / "1-active" / "study.md"
        write(f, SAMPLE, newline="\r\n")
        before = f.read_bytes()

        task = W.set_pu("T-261001-1", 2, 2, root=root)
        assert (task.p, task.u) == (2, 2)
        assert task.status == "todo"  # status must not be touched

        after = f.read_bytes()
        old_lines = before.decode("utf-8").split("\n")
        new_lines = after.decode("utf-8").split("\n")
        assert len(old_lines) == len(new_lines)
        changed = [i for i, (a, b) in enumerate(zip(old_lines, new_lines)) if a != b]
        assert changed == [2], f"only line 3 should change, got {changed}"
        assert new_lines[2] == "- [ ] T-261001-1 First task #P2 #U2\r"


@test
def test_invalid_p_and_u_are_rejected():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        write(root / "1-active" / "x.md", SAMPLE)
        for p, u in ((0, 1), (1, 4), (4, 4)):
            try:
                W.set_pu("T-261001-1", p, u, root=root)
            except ValueError:
                continue
            raise AssertionError(f"{p},{u} should be rejected")


# ---------------------------------------------------------------- create


@test
def test_new_task_uses_todays_sequence():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        f = root / "1-active" / "study.md"
        write(f, "- [ ] T-261018-3 Existing #P1 #U1\n- [x] T-261018-4 Done #P1 #U3\n")

        task = W.create_task(
            file="1-active/study.md", title="A new task",
            p=1, u=2, tags=["backend", "#React"], ddl="2026-10-30",
            root=root, today=TODAY,
        )
        assert task.id == "T-261018-5", task.id
        assert task.title == "A new task"
        assert task.p == 1 and task.u == 2
        assert task.tags == ["backend", "React"]  # the leading # is stripped
        assert task.ddl == "2026-10-30"
        assert task.status == "todo"


@test
def test_new_task_appends_and_keeps_the_newline_style():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        f = root / "1-active" / "a.md"
        write(f, SAMPLE, newline="\r\n")
        before = f.read_bytes()

        W.create_task(file="1-active/a.md", title="appended", p=3, u=3, root=root, today=TODAY)
        after = f.read_bytes()

        assert after.startswith(before), "existing bytes must be a prefix, untouched"
        assert after.count(b"\r\n") == before.count(b"\r\n") + 1
        assert b"- [ ] T-261018-1 appended" in after


@test
def test_new_task_preserves_bom_presence():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        f = root / "1-active" / "bom.md"
        write(f, "- [ ] T-261001-1 As is #P1 #U1\n", bom=True)
        assert f.read_bytes().startswith(b"\xef\xbb\xbf")
        W.create_task(file="1-active/bom.md", title="new", root=root, today=TODAY)
        data = f.read_bytes()
        assert data.startswith(b"\xef\xbb\xbf"), "the BOM must not be lost"
        assert data.count(b"\xef\xbb\xbf") == 1, "the BOM must not be duplicated"


@test
def test_no_bom_is_not_invented():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        write(root / "1-active" / "x.md", "- [ ] T-261001-1 As is #P1 #U1\n")
        W.create_task(file="1-active/x.md", title="new", root=root, today=TODAY)
        assert not (root / "1-active" / "x.md").read_bytes().startswith(b"\xef\xbb\xbf")


@test
def test_empty_title_is_rejected():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        write(root / "1-active" / "x.md", SAMPLE)
        for bad in ("", "   "):
            try:
                W.create_task(file="1-active/x.md", title=bad, root=root, today=TODAY)
            except ValueError:
                continue
            raise AssertionError(f"empty title must be rejected: {bad!r}")


@test
def test_missing_file_raises():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        write(root / "1-active" / "x.md", SAMPLE)
        try:
            W.create_task(file="1-active/does-not-exist.md", title="x", root=root, today=TODAY)
        except (LookupError, FileNotFoundError):
            return
        raise AssertionError("a missing file must raise")


@test
def test_templates_and_readme_are_read_only():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        write(root / "1-active" / "_project-template.md", SAMPLE)
        write(root / "README.md", SAMPLE)
        for f in ("1-active/_project-template.md", "README.md"):
            try:
                W.create_task(file=f, title="x", root=root, today=TODAY)
            except ValueError:
                continue
            raise AssertionError(f"{f} must be rejected")
        assert all("T-261018" not in (root / f).read_text(encoding="utf-8") for f in
                   ("1-active/_project-template.md", "README.md"))


@test
def test_path_escape_is_rejected():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d) / "tasks"
        outside = Path(d) / "outside.md"
        write(outside, SAMPLE)
        write(root / "1-active" / "x.md", SAMPLE)
        for bad in ("../outside.md", "1-active/../../outside.md"):
            try:
                W.create_task(file=bad, title="x", root=root, today=TODAY)
            except (ValueError, LookupError):
                continue
            raise AssertionError(f"{bad} must be rejected")
        assert "T-261018" not in outside.read_text(encoding="utf-8")


@test
def test_duplicate_id_fails_without_editing():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        write(root / "1-active" / "a.md", "- [ ] T-261001-1 A #P1 #U1\n")
        write(root / "1-active" / "b.md", "- [ ] T-261001-1 B #P1 #U1\n")
        before = (root / "1-active" / "a.md").read_bytes()
        try:
            W.set_status("T-261001-1", "done", root=root, today=TODAY)
        except ValueError as exc:
            assert "duplicate" in str(exc)
        else:
            raise AssertionError("a duplicate ID must raise")
        assert (root / "1-active" / "a.md").read_bytes() == before, "no half-written file on error"


# ---------------------------------------------------------------- whole-line rewrite


@test
def test_title_change_touches_one_line():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        f = root / "1-active" / "study.md"
        write(f, SAMPLE, newline="\r\n")
        before = f.read_bytes()

        task = W.update_task("T-261001-1", {"title": "Renamed title"}, root=root)
        assert task.title == "Renamed title"
        assert task.p == 1 and task.u == 1  # fields not passed are untouched
        assert task.status == "todo"

        after = f.read_bytes()
        old_lines = before.decode("utf-8").split("\n")
        new_lines = after.decode("utf-8").split("\n")
        assert len(old_lines) == len(new_lines)
        changed = [i for i, (a, b) in enumerate(zip(old_lines, new_lines)) if a != b]
        assert changed == [2], changed
        assert new_lines[2].endswith("\r"), "CRLF must be preserved"


@test
def test_setting_and_clearing_ddl():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        f = root / "1-active" / "x.md"
        write(f, SAMPLE)

        W.update_task("T-261001-2", {"ddl": "2026-11-01"}, root=root)
        tasks = P.parse_file(f, root)
        assert [t for t in tasks if t.id == "T-261001-2"][0].ddl == "2026-11-01"

        W.update_task("T-261001-2", {"ddl": None}, root=root)
        tasks = P.parse_file(f, root)
        t = [t for t in tasks if t.id == "T-261001-2"][0]
        assert t.ddl is None
        assert "DDL:" not in t.raw


@test
def test_tag_and_priority_change():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        f = root / "1-active" / "x.md"
        write(f, SAMPLE)

        task = W.update_task(
            "T-261001-1", {"tags": ["backend", "#React"], "p": 2, "u": 3}, root=root
        )
        assert task.tags == ["backend", "React"]
        assert (task.p, task.u) == (2, 3)


@test
def test_marking_done_from_the_drawer_stamps_done():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        f = root / "1-active" / "x.md"
        write(f, SAMPLE)
        task = W.update_task("T-261001-1", {"status": "done"}, root=root, today=TODAY)
        assert task.status == "done"
        assert task.done == "2026-10-18"
        assert "DONE:2026-10-18" in task.raw


@test
def test_editing_to_an_empty_title_is_rejected():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        write(root / "1-active" / "x.md", SAMPLE)
        for bad in ("", "   "):
            try:
                W.update_task("T-261001-1", {"title": bad}, root=root)
            except ValueError:
                continue
            raise AssertionError("an empty title must be rejected")


# ---------------------------------------------------------------- delete


@test
def test_delete_removes_the_task_and_its_details():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        f = root / "1-active" / "study.md"
        write(f, SAMPLE, newline="\r\n")

        res = W.delete_task("T-261001-1", root=root)
        assert res["removedLines"] == 3, res  # the task line plus two detail lines
        assert res["title"] == "First task"

        text = f.read_text(encoding="utf-8")
        assert "T-261001-1" not in text
        assert "detail line one" not in text and "detail line two" not in text
        # Other tasks and the newline style are unaffected
        assert "T-261001-2" in text
        # Count bytes: read_text() would normalise \r\n to \n
        assert f.read_bytes().count(b"\r\n") == 4  # 7 lines originally, 3 removed


@test
def test_deleting_a_missing_task_leaves_the_file_alone():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        f = root / "1-active" / "x.md"
        write(f, SAMPLE)
        before = f.read_bytes()
        try:
            W.delete_task("T-999999-9", root=root)
        except LookupError:
            pass
        else:
            raise AssertionError("a missing task must raise")
        assert f.read_bytes() == before, "the file must not change on error"


# ---------------------------------------------------------------- consistency


@test
def test_response_fields_match_to_dict():
    """TaskOut is a hand-written copy; something must stop it from drifting."""
    from main import TaskOut

    task = P.Task(id="T-1", status="todo", title="x")
    assert set(task.to_dict()) == set(TaskOut.model_fields), (
        set(task.to_dict()) ^ set(TaskOut.model_fields)
    )


@test
def test_write_then_reparse_round_trips():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        write(root / "1-active" / "x.md", SAMPLE)
        W.create_task(file="1-active/x.md", title="verify", p=2, u=1,
                      tags=["output"], ddl="2026-11-01", root=root, today=TODAY)
        tasks = P.parse_file(root / "1-active" / "x.md", root)
        last = tasks[-1]
        assert last.title == "verify"
        assert (last.p, last.u) == (2, 1)
        assert last.tags == ["output"]
        assert last.quadrant == "Q3"


# ---------------------------------------------------------------- ids


@test
def test_assign_id_fills_a_missing_id():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        f = root / "1-active" / "x.md"
        write(f, "- [ ] Hand written task #P1 #U1\n")

        task = W.assign_id("1-active/x.md", 1, "- [ ] Hand written task #P1 #U1",
                           root=root, today=TODAY)
        assert task.id == "T-261018-1", task.id
        assert task.title == "Hand written task"
        raw = f.read_text(encoding="utf-8")
        assert raw.startswith("- [ ] T-261018-1 Hand written task #P1 #U1")
        assert raw.count("\n") == 1, "no extra lines"


@test
def test_assign_id_is_idempotent():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        f = root / "1-active" / "x.md"
        write(f, "- [ ] T-261001-7 Already tagged #P1 #U1\n")
        before = f.read_bytes()
        task = W.assign_id("1-active/x.md", 1, "- [ ] T-261001-7 Already tagged #P1 #U1",
                           root=root, today=TODAY)
        assert task.id == "T-261001-7"
        assert f.read_bytes() == before, "an existing ID must not change"


@test
def test_assign_id_refuses_a_changed_line():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        write(root / "1-active" / "x.md", "- [ ] Hand written task\n")
        try:
            W.assign_id("1-active/x.md", 1, "- [ ] Something else", root=root, today=TODAY)
        except RuntimeError:
            return
        raise AssertionError("a mismatched line must be refused")


@test
def test_repair_renumbers_duplicates_and_keeps_the_first():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        a = root / "1-active" / "a.md"
        b = root / "1-active" / "b.md"
        write(a, "- [ ] T-261018-3 First #P1 #U1\n")
        write(b, "- [ ] T-261018-3 Second #P1 #U2\n")

        res = W.repair_duplicate_ids(root=root, today=TODAY)
        assert res["changed"] == 1, res
        assert "T-261018-3 First" in a.read_text(encoding="utf-8"), "first must keep its ID"
        second = b.read_text(encoding="utf-8")
        assert "T-261018-3" not in second
        assert "T-261018-4 Second" in second, second
        # nothing else touched
        assert second.count("\n") == 1


@test
def test_repair_is_a_noop_without_duplicates():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        f = root / "1-active" / "a.md"
        write(f, "- [ ] T-261018-1 A #P1 #U1\n- [ ] T-261018-2 B #P1 #U2\n")
        before = f.read_bytes()
        res = W.repair_duplicate_ids(root=root, today=TODAY)
        assert res["changed"] == 0
        assert f.read_bytes() == before


# ---------------------------------------------------------------- tags / tracks


@test
def test_add_tag_is_idempotent_and_case_insensitive():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        f = root / "1-active" / "x.md"
        write(f, SAMPLE)

        t = W.add_tag("T-261001-1", "TopN", root=root)
        assert "TopN" in t.tags
        t2 = W.add_tag("T-261001-1", "topn", root=root)
        assert [x.lower() for x in t2.tags].count("topn") == 1, t2.tags
        # Everything else on the line is untouched
        assert "- [ ] T-261001-1 First task" in f.read_text(encoding="utf-8")


@test
def test_move_to_someday_moves_line_and_details():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        src = root / "1-active" / "study.md"
        dst = root / "4-someday.md"
        write(src, SAMPLE, newline="\r\n")
        write(dst, "# 4-someday\n\n- 2026-10-20 — an idea\n")

        res = W.move_to_someday("T-261001-1", root=root)
        assert res["movedLines"] == 3, res
        assert res["to"] == "4-someday.md"

        src_text = src.read_text(encoding="utf-8")
        assert "T-261001-1" not in src_text
        assert "detail line one" not in src_text
        # The other task stays put and keeps CRLF
        assert "T-261001-2" in src_text
        assert src.read_bytes().count(b"\r\n") > 0

        dst_text = dst.read_text(encoding="utf-8")
        assert "T-261001-1 First task" in dst_text
        assert "detail line one" in dst_text
        # The existing idea survived
        assert "2026-10-20 — an idea" in dst_text
        # No CRLF leaked into an LF file
        assert dst.read_bytes().count(b"\r\n") == 0


@test
def test_move_to_someday_missing_file_is_refused():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        write(root / "1-active" / "x.md", SAMPLE)
        try:
            W.move_to_someday("T-261001-1", root=root)
        except LookupError:
            pass
        else:
            raise AssertionError("a missing 4-someday.md must raise")
        assert "T-261001-1" in (root / "1-active" / "x.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------- details


@test
def test_set_details_adds_a_block_under_the_task():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        f = root / "1-active" / "x.md"
        write(f, SAMPLE)

        task = W.set_details("T-261001-2", ["first line", "  - a bullet"], root=root)

        assert task.detail == ["  first line", "  - a bullet"], task.detail
        text = f.read_text(encoding="utf-8")
        assert "- [ ] T-261001-2 Second task #P1 #U3 DDL:2026-10-20\n  first line\n  - a bullet\n" in text
        # the neighbour above keeps its own block untouched
        assert "      detail line one\n      detail line two\n" in text


@test
def test_set_details_replaces_the_existing_block():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        f = root / "1-active" / "x.md"
        write(f, SAMPLE, newline="\r\n")

        task = W.set_details("T-261001-1", ["only one line"], root=root)

        assert task.detail == ["  only one line"]
        data = f.read_bytes()
        assert data.count(b"\n") == data.count(b"\r\n"), "CRLF must survive the edit"
        text = f.read_text(encoding="utf-8")
        assert "detail line two" not in text
        assert "- [ ] T-261001-2 Second task" in text, "the next task must survive"


@test
def test_set_details_with_an_empty_list_removes_the_block():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        f = root / "1-active" / "x.md"
        write(f, SAMPLE)

        task = W.set_details("T-261001-1", [], root=root)

        assert task.detail == []
        text = f.read_text(encoding="utf-8")
        assert "detail line" not in text
        assert text.count("\n\n") >= 1, "the blank separator line must stay"


@test
def test_set_details_ignores_blank_lines_and_keeps_the_task_line():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        f = root / "1-active" / "x.md"
        write(f, SAMPLE)
        before = f.read_text(encoding="utf-8").split("\n")

        task = W.set_details("T-261001-1", ["", "a", "   ", "b"], root=root)

        assert task.detail == ["  a", "  b"]
        after = f.read_text(encoding="utf-8").split("\n")
        assert after[2] == before[2], "the task line itself must be byte-identical"


@test
def test_set_details_rejects_an_unknown_id():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        write(root / "1-active" / "x.md", SAMPLE)
        try:
            W.set_details("T-261001-9", ["x"], root=root)
        except LookupError:
            pass
        else:
            raise AssertionError("an unknown id must raise LookupError")


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
