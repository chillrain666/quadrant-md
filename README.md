# Quadrant

**A markdown-first todo system for humans and AI agents.**
One line per task, one file per project — no database, no account, no cloud lock-in.

[中文说明](README.zh-CN.md) · [Design notes](docs/design.md) · [Agent skill](skill/quadrant/SKILL.md)

<p align="center">
  <img src="docs/screenshot-board.png" alt="Quadrant board: a 3x3 importance x urgency grid" width="100%">
</p>

Your todos are a pile of `.md` files. Edit them in Obsidian, VSCode, vim or on your
phone; or just tell an AI agent "turn the API error codes into a table before Friday"
and let it write the right line. The built-in board is optional cosmetics — **without
it, `grep` and an editor still work**.

## Why another todo app?

| | Notion / Todoist | Obsidian plugins | **Quadrant** |
| --- | --- | --- | --- |
| Where the data lives | someone else's server | local markdown | **local markdown (single source of truth)** |
| Offline | ✗ | ✓ | ✓ |
| `git log` your decisions | ✗ | half | ✓ |
| An AI agent can read/write it safely | ✗ API + OAuth | ✗ bespoke format | **✓ it is one line of text** |
| Drag ordering | ✓ | depends | ✓ (order kept aside, never pollutes markdown) |
| Priority / quadrants | ✓ | varies | **P×U grid, encoded as `#P1 #U2`** |

Three ideas hold it together:

1. **Capture is free** — unclear things go to `0-inbox.md`, one line each, unsorted.
2. **Priority is a field, not a position** — changing it edits one character
   (`#P2` → `#P1`) instead of moving paragraphs.
3. **The agent touches only the line that changed** — line order, indented details and
   newline style are untouched, so humans and agents can edit the same files.

## Quick start

```bash
git clone https://github.com/chillrain666/quadrant-md.git
cd quadrant-md
python scripts/init_tasks.py          # creates tasks/ (directories + demo data)
cd app
uv sync                               # or: pip install -r requirements.txt
uv run python main.py                 # -> http://127.0.0.1:8000 (steps to a free port if busy)
```

If the grid appears, you are done. The frontend build ships with the repo, **no Node
required**.

Point it at an existing notes directory instead:

```bash
TASKS_ROOT=/path/to/my/tasks uv run python main.py        # macOS / Linux
set TASKS_ROOT=D:\notes\tasks && uv run python main.py    # Windows
```

## The directory *is* the database

```
tasks/
├── 0-inbox.md       capture box: anything not thought through (never on the board)
├── 1-active/        in progress, one file per project      <- the only board source
│   ├── study/study.md
│   └── life/chores/chores.md
├── 2-notes/         long details (not scanned)
├── 3-log/           timeline log, append only (not scanned)
├── 4-someday.md     "one day" items + ideas (own panel)
├── 5-archive/       finished projects (not scanned)
└── watch/           lists: shows, books, serials (own panel, no P/U)
```

Four tracks, each with its own surface: tasks reach the quadrants, lists do not, ideas go
to someday, and captured items are shown **nowhere**. That last one is deliberate — once
captured items are visible, people start tidying them, which defeats capture.

## What one task looks like

```markdown
- [ ] T-261021-1 Read chapter 3 of DDIA #P1 #U2 #reading DDL:2026-11-05
      indented lines are details of this task, kept verbatim, deleted with it
```

| Piece | Meaning |
| --- | --- |
| `- [ ]` `- [x]` `- [-]` | to do / done / blocked |
| `T-261021-1` | globally unique ID: `T-` + `YYMMDD` + `-` + daily sequence, immutable |
| `#P1`~`#P3` | importance, P1 highest |
| `#U1`~`#U3` | urgency, U1 highest |
| `#tag` | several allowed, CJK / capitals / `a/b` all fine |
| `DDL:2026-11-05` | due date |
| `DONE:2026-10-21` | completion date (stamped when you tick) |

**Quadrants are computed from `P × U`, never stored**, so changing priority is a
two-character edit. The board draws a 3×3 grid (one row per P, one column per U) because
each axis has three levels; forcing that into four cells throws information away.

## Built for AI agents

`skill/quadrant/` is an agent skill in the `SKILL.md` shape used by Claude Agent Skills,
pi, Cursor and friends. Drop it into your agent's skills directory and it knows:

- which file a sentence belongs to ("note this" → inbox, "this week" → active,
  "someday" → someday, "started watching X" → watch)
- how to write without damaging the file (append only, edit one line, per-file newline
  style, compute the ID)
- how to run the board and how to do a weekly review

A conversation looks like this:

> **You:** note that I want to try a two-week review cycle
> **Agent:** wrote to `tasks/0-inbox.md`: `- Try a two-week review cycle`

> **You:** turn the API error codes into a table before Friday, it matters
> **Agent:** wrote to `tasks/1-active/work/demo-project.md`:
> `- [ ] T-261021-18 Turn the API error codes into a table #P2 #U1 #work DDL:2026-10-23`

> **You:** done with that one
> **Agent:** `- [x] ... DONE:2026-10-23` (two spots changed)

Install for pi:

```bash
cp -r skill/quadrant ~/.pi/agent/skills/
```

For Claude Code or any other client that supports skills, copy `skill/quadrant/` into its
skills directory. Clients without skills support can still use `SKILL.md` as a rules file.

## Board features

- **3×3 grid**: one row per P, one column per U; empty cells stay visible
- **Search**: title / detail lines / tags / project / directory / ID, case-insensitive,
  synonym-aware
- **Filters**: independent P and U axes, due window, status, directory cascade, tags
- **Editing**: click a task for a compact centred dialog (title / P / U / status / DDL /
  tags / detail lines)
- **Write-back**: ticking stamps `DONE:`, plus create, delete and drag, all editing
  markdown directly
- **Focus**: tag tasks `#TopN` and they sort themselves "overdue → today → P1U1 → …"
- **Following**: shows and books in their own tab, no quadrants (`tasks/watch/`)
- **Someday**: cards with a summary, full text on click, draggable in four directions
- **Drag onto a tab**: drop a task on **Focus** to tag it `#TopN`, drop it on **someday**
  to move the whole task (line + details) into `4-someday.md`
- **Search inside every panel**: the search box filters board, Focus, Following and someday
  alike
- **Details written back**: the dialog edits the indented Markdown lines under the task
  and saves straight into the file
- **No ID? No problem**: a hand-written task without an ID gets one automatically the
  first time you edit it; duplicate IDs are detected and repaired in one click
- **Language switch**: English / 中文, remembered per browser

<p align="center">
  <img src="docs/screenshot-focus.png" width="49%" alt="Focus view">
  <img src="docs/screenshot-someday.png" width="49%" alt="Someday cards">
</p>

Drag order is **never written into markdown**: the board keeps one global order in
`app/.order.json`, and the secondary panels keep per-panel lists in `app/.lists.json`.
Both are derived state — delete them and the default order returns.

## The lineage (what this borrows, honestly)

This is not a new idea so much as a careful recombination of well-known ones:

- **Importance × urgency** comes from the **Eisenhower Matrix** — attributed to Dwight D.
  Eisenhower's "what is important is seldom urgent" remark, and popularised for ordinary
  people by **Stephen R. Covey** in *The 7 Habits of Highly Effective People* (1989).
  Quadrant nudges it from 2×2 to **3×3**, because a two-level axis forces you to lie about
  "medium".
- **The capture inbox, the "someday/maybe" list and the weekly review** are the three
  habits that make **David Allen's _Getting Things Done_** (2001) work. This system takes
  exactly those three and drops the rest.
- **One line per task, greppable, plain text** follows the **todo.txt** convention
  (Gina Trapani, 2007) and the wider local-first / plain-text movement around
  **Obsidian** — files over databases, `git` over sync services.
- **Agent-native packaging** follows **Anthropic's Agent Skills** (`SKILL.md`): the
  operating manual ships next to the data, so any agent can pick it up.
- The first draft of the markdown contract was written with **Doubao** (ByteDance's
  assistant) in October 2026, then reshaped over two weeks of daily use: the 3×3 grid,
  the three tracks, the global total order and the "touch one line" write-back rules all
  came from things that broke in practice.

If you are here from the productivity side: the interesting part is not the grid, it is
that **the file is the API**.

## Code layout

```
app/          FastAPI backend + React frontend (no third-party UI or drag library)
  parser.py     read-only: scan, parse, filter, group, Focus ordering
  writer.py     write-back: touch one line, re-parse and verify, restore on mismatch
  order.py      board order: one global total order, stored in .order.json
  lists.py      panel order: per-scope lists in .lists.json
  synonyms.py   synonym table shared by search, tag filters and Focus
  web/          React 19 + TS + Vite (already built into dist/)
skill/quadrant/ agent skill: SKILL.md + references (grammar, layout, recipes, panel, review)
templates/tasks/ the data-directory template copied by init_tasks.py
scripts/      init_tasks.py, screenshot.mjs
```

## Tests

```bash
cd app && uv run python run_tests.py    # 100+ assertions, all in temp directories
```

## Design trade-offs (on purpose)

- **Order is not in markdown**: writing it there means reordering files on every drag,
  huge diffs, and a fight between "human edits the md" and "the board drags".
- **Grouping ≠ filtering**: due buckets are mutually exclusive; the `due=week` filter is a
  rolling seven days including today.
- **The date in the ID is the creation date**: no collisions across years and no "what
  number am I on" bookkeeping.
- **No cloud sync**: the data is your files, sync them with git / Syncthing / iCloud.

## Roadmap

- [ ] Savable multi-filter views
- [ ] Indexing / caching beyond a few thousand tasks

## License

MIT
