# Directory layout and the four tracks

## Why "directories are semantics"

No database, no tag tree: **the filesystem is the taxonomy**.

- One file = one project; a directory = a group of projects. New category? New folder,
  zero code changes.
- Copy the folder and you copied every todo (including `git log`).
- Any editor works: Obsidian, VSCode, vim, a phone memo app.

The accepted cost: directory levels do not automatically become filters. "Project" on
the board is the **file name**.

## Standard layout

```
tasks/
├── 0-inbox.md              capture box (never shown)
├── 1-active/               <- the only source for the quadrant board
│   ├── study/study.md
│   ├── life/chores/chores.md
│   ├── work/demo-project.md
│   └── _project-template.md    leading underscore = template, not scanned
├── 2-notes/                long details (not scanned)
│   └── _note-template.md
├── 3-log/                  timeline log (not scanned)
│   └── 2026-W43.md
├── 4-someday.md            one day / ideas (own panel)
├── 5-archive/              archive (not scanned)
├── follow/                  list track (own panel)
│   ├── shows.md
│   └── books.md
└── README.md               format contract (not scanned)
```

Scanning rules live at the top of `app/parser.py` (`INCLUDE_DIRS`, `FOLLOW_DIRS`,
`SOMEDAY_FILES`, `EXCLUDE_DIRS`, `EXCLUDE_PREFIXES`) — that is the single place to edit.

## Four tracks, each with its own panel

| Track | `kind` | Source | P/U? | Where it shows |
| --- | --- | --- | --- | --- |
| Tasks | `task` | `1-active/**` | yes, expected | quadrant grid / search / Focus |
| Lists | `follow` | `follow/` | no | "Follow" tab |
| Later | `someday` | `4-someday.md` | no | "someday" tab (cards) |
| Capture | — | `0-inbox.md` | no | **nowhere** |

`0-inbox.md` is deliberately invisible: once captured items are on screen, people start
tidying them, and the whole point of capture is not tidying yet. Clearing the inbox is
an explicit step of the weekly review (see `weekly-review.md`).

## Four kinds of file identity

| Shape | Meaning |
| --- | --- |
| `1-active/study/study.md` | project "study", group path `["1-active","study"]` |
| `1-active/_project-template.md` | template: leading `_`, **never scanned** |
| `5-archive/2026/x.md` | archive: the whole directory is **not scanned** |
| `2-notes/x.md` | long detail: outside the scan scope, linked from a task line |

## Switching data directories

The data directory is fully decoupled from the code:

```bash
export TASKS_ROOT=/path/to/my/tasks       # Linux / macOS
setx TASKS_ROOT "D:\notes\tasks"          # Windows (new terminal)
```

Without `TASKS_ROOT` the default is `<repo>/tasks` (the parent of `app/`). `/api/meta`
echoes the effective path — check it first when "my tasks are not showing up".

The follow track's directory name is configurable too, for data directories that already
use another name (a localized folder, for example):

```bash
FOLLOW_DIRS=lists uv run python main.py      # several names: FOLLOW_DIRS=follow,lists
```
