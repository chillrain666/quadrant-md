---
name: quadrant
description: |
  Markdown-first todo system + local board. Use when the user wants to manage a todo list,
  an inbox, a someday list, a follow list, priorities/quadrants (P×U, importance/urgency,
  Eisenhower matrix), daily capture, task IDs, a weekly review, or wants a local kanban
  board that reads plain .md files — 待办 / 待办系统 / 记一下 / 加个待办 / 今天做什么 /
  这周计划 / 灵感记一下 / 将来某天 / 收件箱 / 优先级 / 重要不紧急 / 四象限 / 九宫格 /
  周复盘 / 归档 / 日报 / 周报 / 总结 / 今天我做了什么 / 这周做了什么 / standup /
  weekly report / summarize my week.
  Writes into plain markdown (one line per task) instead of a database, so any editor and
  any agent share the same source of truth. Not for calendar reminders or alarms (use the
  user's reminder app) and not for note-taking apps with their own storage format.
---

# Quadrant · a markdown todo system (agent handbook)

One sentence: **todos are a pile of markdown files.** This skill covers (1) the format
you read and write, (2) how to turn what the user says into exactly the right line,
and (3) how to run the local board.

The board is optional cosmetics — without it, `grep` plus an editor still works.

## 0. Check the situation first (30 seconds)

```
Where is the data?   -> ask, or read TASKS_ROOT; default is <repo>/tasks
Is it initialised?   -> does 1-active/ and 4-someday.md exist?
Is the board running? -> http://127.0.0.1:8000
```

First use (no data directory yet):

```bash
python scripts/init_tasks.py                 # creates <repo>/tasks (templates + demo data)
python scripts/init_tasks.py --root ~/notes/tasks
export TASKS_ROOT=~/notes/tasks              # Windows: setx TASKS_ROOT ...
```

The data directory (this one level *is* the whole database):

```
tasks/
  0-inbox.md        capture box: anything not thought through yet
  1-active/         in progress: one file per project        <- the board reads only this
    study/study.md
    life/chores/chores.md
  2-notes/          long details, not scanned
  3-log/            timeline log, append only, not scanned
  4-someday.md      "one day" items + ideas
  5-archive/        finished projects, not scanned
  follow/            list track: shows / serials / books, no P/U
  README.md         the format contract (for humans)
```

See `references/directory-layout.md`.

## 1. What a task line looks like (the one format to remember)

```markdown
- [ ] T-261021-1 Task title #P1 #U2 #tag DDL:2026-11-05
      indented lines are details of this task, kept verbatim, also searched
```

| Piece | Meaning |
| --- | --- |
| `- [ ]` / `- [x]` / `- [-]` | to do / done / blocked |
| `T-261021-1` | globally unique ID: `T-` + `YYMMDD` + `-` + daily sequence; **never changed** |
| `#P1`~`#P3` | importance, P1 is the highest |
| `#U1`~`#U3` | urgency, U1 is the highest |
| `#any-tag` | several allowed; CJK, capitals and `a/b` are fine |
| `DDL:YYYY-MM-DD` | due date |
| `DONE:YYYY-MM-DD` | completion date (added when ticking) |

**Only flush-left** `- [ ]` starts a task; indented lines belong to the task above.
Lines without an ID are not tasks (except in `4-someday.md`, where free bullets count).

Full grammar, quadrant mapping and edge cases: `references/md-conventions.md`.

## 2. The user says something — which file changes?

| The user says | Goes to | How |
| --- | --- | --- |
| "note that X" / "an idea" / no time mentioned | end of `0-inbox.md` | append `- X`, **no** ID, P or U |
| "I need to finish X this week" / a deadline | end of `1-active/<project>.md` | allocate an ID, add `#P`/`#U` and `DDL:` |
| "park X for later" / "I'd like to learn X someday" | end of `4-someday.md` | append `- X` (ID optional) |
| "started following X" | `follow/shows.md` | append `- [ ] T-... X #shows`, no P/U |
| "X is done" | the original line | `[ ]` -> `[x]`, add `DONE:<today>` |
| "drop X / X is stuck" | the original line | `[ ]` -> `[-]` (blocked) |
| "make X P1 / more urgent" | the original line | change only `#P?` / `#U?` |
| "remove X" | the original file | delete that line plus its indented details |
| "what did I do this week" | `3-log/` | append a log entry, **never** touch `1-active/` |

When in doubt: **if it can go to inbox, do not put it in active.** Capture beats tidying.

Default P/U heuristics (when the user did not say): a hard, near deadline -> `U1`;
it moves a long-term goal -> `P1`; a quick errand -> `P3 #U1`. If unsure, **fill in only
the axis you are confident about** rather than guessing both. Explicit user preferences
always win.

## 3. Write-back rules (breaking them damages the user's files)

1. **Touch only the line that changed.** Line order, other lines, indented details,
   blank lines and newline style (CRLF/LF, per file) are untouched.
2. **Append, never insert.** New tasks go at the end of the file (except `3-log/`,
   which is chronological anyway).
3. **Compute the ID now**: `T-<YYMMDD>-<N>`, where `N` is the largest sequence used
   today in that data directory plus one (across all files). If the user says "no ID,
   just add the task", `POST /api/ids/assign` (or writer.assign_id) fills it in later;
   never guess an ID that already exists.
4. **Never reorder.** Board drag order lives in the app's `.order.json` and is **never
   written into markdown**.
5. **Read it back**: re-parse the affected lines after writing; if it does not match,
   restore the original bytes and tell the user.
6. **Do not reformat the file**: no whitespace normalisation, no adding `DONE`, nothing
   the user did not ask for.

## 4. Run the board (optional)

```bash
cd app
uv sync                                    # or: pip install -r requirements.txt
uv run python main.py                      # -> http://127.0.0.1:8000
TASKS_ROOT=/path/to/tasks uv run python main.py   # use another data directory
```

The frontend build ships in `app/web/dist`, so Node is not required to run it. Only
rebuilding the UI needs `cd app/web && npm install && npm run dev`.

Board features: 3x3 grid (P×U), search, filters, grouping, drawer editing, tick
write-back, delete, drag ordering, Focus (`#TopN`), follow panel, someday cards,
synonym table. Details and the API list: `references/panel.md`.

## 5. Weekly review (the only mandatory ritual)

When the user says "review / how did this week go / tidy up", follow
`references/weekly-review.md`: count completions, clear the inbox, move someday items,
archive finished projects, and set next week's Focus.

## 6. Summaries (daily / weekly)

When the user asks for a 日报 / 周报 / summary / "what did I do this week":

- **Evidence only.** A task counts as done only if it carries `DONE:<date>`. Never
  promote "basically finished" into `Done`.
- **Daily** = today's `DONE:` items + what is blocked + tomorrow's next. 5–8 lines.
- **Weekly** = shipped / slipped / where the week went / blocked / next week's Focus.
  Half a page, with counts, not a backlog dump.
- Save it to `3-log/` (daily: `YYYY-MM/YYYY-MM-DD.md`, weekly: `YYYY-Www.md`),
  append-only. Reporting is **read-only** unless the user asks for changes.

Full templates and the exact commands: `references/summaries.md`.

## 7. Reference files

- `references/directory-layout.md` -- directory hierarchy, four tracks, what is skipped
- `references/md-conventions.md` -- line grammar, ID rules, quadrants, `^T-xxx` block refs
- `references/agent-recipes.md` -- common requests turned into exact commands/edits
- `references/panel.md` -- starting the board, ports, API, troubleshooting
  (including the one-click duplicate-ID repair and the EN/中文 switch)
- `references/weekly-review.md` -- the weekly review checklist (the ritual)
- `references/summaries.md` -- daily / weekly report templates and the commands that
  gather the evidence
