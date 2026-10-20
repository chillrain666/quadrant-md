# The board: running it, features, API, troubleshooting

## Start

```bash
cd app
uv sync                                          # first run: fastapi + uvicorn
uv run python main.py                            # -> http://127.0.0.1:8000
uv run python main.py --port 8010                # port already taken
TASKS_ROOT=/path/to/tasks uv run python main.py  # point at another data directory
WATCH_DIRS=watch,lists uv run python main.py    # watch-track folder names (comma separated)
```

No `uv`? `python -m venv .venv && .venv/Scripts/pip install -r requirements.txt`
(or pipx).

The frontend build ships with the repo (`app/web/dist`), so **Node is not required**.
Only UI changes need:

```bash
cd app/web && npm install && npm run build     # production
cd app/web && npm run dev                      # development (5173, /api proxied to 8000)
```

## What the board does

| Area | Capability |
| --- | --- |
| Default view | P x U 3x3 grid; empty cells are drawn too (you can see what is missing) |
| Search | title / detail lines / tags / project / directory / ID, case-insensitive, synonym-aware |
| Filters | independent P and U axes; due window (today/week/month/overdue/none); status; directory cascade; tags |
| Grouping | grid / merged quadrants / project / due / status |
| Editing | click a task -> right-hand drawer: title, P, U, status, DDL, tags |
| Write-back | tick, create, delete, drag: all edit markdown directly |
| Focus | tasks tagged `#TopN` (or a synonym), ordered "overdue -> today -> P1U1 -> ...", limit adjustable |
| Watch | `watch/` lists grouped by file, no P/U |
| Someday | `4-someday.md` cards: summary only, click to read, drag in four directions |

## How order is stored

- Board (inside a cell / across cells): `.order.json` -- **one global total order** with
  fractional ranks, only for items that were dragged. A drop lands **flush against the
  anchor**, using *global* neighbours rather than the ones visible in the current view.
- Focus / Watch / Someday: `.lists.json`, one full list per panel.
- Both files are **derived state**: delete them and the default order (ID order / rule
  order) comes back. No content is lost.

## API

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/api/tasks` | `q` `p` `u` `tag` `status` `project` `dir` `due` `include_done` `group_by` |
| GET | `/api/meta` | tags, directory tree, files, counts, synonyms, format self-check, `tasksRoot` |
| GET | `/api/focus` | tasks tagged `#TopN`, rule-sorted (`q` searches within Focus) |
| GET | `/api/watch` | watch lists, grouped by file (`q` searches within the lists) |
| GET | `/api/someday` | someday entries, single group (`q` searches within it) |
| POST | `/api/tasks` | create |
| PATCH | `/api/tasks/{id}` | change `status` / `p` / `u` / `title` / `tags` / `ddl` (send only what changes) |
| DELETE | `/api/tasks/{id}` | delete (line plus indented details) |
| PUT | `/api/order` | drag order (writes `.order.json` only) |
| PUT | `/api/lists` | panel order `{scope, keys}` (writes `.lists.json`) |
| POST | `/api/tasks/{id}/focus` | add the `#TopN` tag (drop on the Focus tab) |
| POST | `/api/tasks/{id}/someday` | move the task into `4-someday.md` (drop on that tab) |
| POST | `/api/ids/assign` | `{file, line, raw}` -> give an ID-less task an ID |
| POST | `/api/ids/repair` | re-number duplicate IDs (first occurrence keeps its own) |
| GET/PUT | `/api/synonyms` | read / replace the synonym table |

Interactive docs: `http://127.0.0.1:8000/docs`.

## Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| Blank page, `/` returns JSON | frontend not built: `cd app/web && npm run build` |
| No tasks visible | check `tasksRoot` in `/api/meta`; does `1-active/` exist? |
| A task disappeared | a missing space after `- [ ]`; the yellow banner lists suspicious lines |
| New routes return 404 | the backend is an old process: restart it |
| Port already taken | automatic: the app steps to the next free port and logs the URL; `--strict-port` to fail instead |
| Order looks odd | delete `app/.order.json` to fall back to ID order |
| "duplicate ID" when saving | the yellow banner offers **Repair IDs**; it re-numbers every occurrence after the first |
| Editing a hand-written task fails | it has no ID yet: the UI assigns one on open (or POST `/api/ids/assign`) |
| Ticking does not change the file | file read-only or locked by an editor; check the terminal |
| Mojibake on the command line | `PYTHONIOENCODING=utf-8` |

## Tests

```bash
cd app && uv run python run_tests.py      # 100+ assertions, all in temp directories
```
