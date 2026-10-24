# Task line grammar

## One task

```markdown
- [ ] T-261021-1 Read chapter 3 of DDIA #P1 #U2 #reading DDL:2026-11-05
      indented lines are details of the task above
      as many lines as needed, kept verbatim, deleted with the task
```

- **Only flush-left** lines starting with `- [ ]` begin a new task.
- Indented lines always belong to the task above; they are not parsed as tasks and do
  not take part in ordering.
- One task occupies "the task line plus every indented line after it".

## Fields

| Piece | Position | Rules |
| --- | --- | --- |
| `[ ]` `[x]` `[-]` | line start | to do / done / blocked (`X` also means done) |
| `T-261021-1` | after the checkbox | `T-` + `YYMMDD` + `-` + daily sequence; **immutable** |
| title | after the ID | up to the first field token; spaces and punctuation allowed |
| `#P1` `#P2` `#P3` | anywhere | importance, P1 is the highest |
| `#U1` `#U2` `#U3` | anywhere | urgency, U1 is the highest |
| `#tag` | anywhere | several allowed; CJK, capitals and `a/b` all work |
| `DDL:2026-11-05` | anywhere | due date; a trailing time is tolerated on read |
| `DONE:2026-10-21` | anywhere | completion date, added when ticking |
| `^T-261021-1` | end of line | block reference (Obsidian); ignored on parse, hidden in the UI |

A `#` in the title becomes a tag, so follow out when writing titles (`C#` is a tag too).
If you really need a literal `#`, use `＃` or rephrase.

## ID rules

- Format `T-<YYMMDD>-<N>`; `YYMMDD` is the **creation date**, `N` the daily sequence.
- `N` = the largest sequence used on that date in this data directory + 1, across all
  files (not per file).
- Computing the next ID:

```bash
# macOS / Linux / Git Bash
grep -rhoE 'T-$(date +%y%m%d)-[0-9]+' tasks | sed 's/.*-//' | sort -n | tail -1
```

```python
# cross-platform and reliable
from pathlib import Path
import re, datetime
root = Path("tasks")
today = datetime.date.today().strftime("%y%m%d")
nums = [int(m) for p in root.rglob("*.md")
        for m in re.findall(rf"T-{today}-(\d+)", p.read_text(encoding="utf-8"))]
next_id = f"T-{today}-{max(nums, default=0) + 1}"
```

> Reference implementation: `app/writer.py: next_id()`.

## Quadrant = P x U, computed, never stored

| Quadrant | Combination | Meaning |
| --- | --- | --- |
| Q1 | `P1` x `U1` | important and urgent: do it now |
| Q2 | `P1` x `U2/U3` | important, not urgent: schedule it (the one people forget) |
| Q3 | `P2/P3` x `U1` | urgent, not important: clear it fast or delegate |
| Q4 | `P2/P3` x `U2/U3` | neither: park it, or delete it |

The board draws a **3x3 grid** (one row per P, one column per U): each axis has three
levels, and collapsing them into four cells would lose the middle.

A task missing P or U is never guessed at; it lands in "unclassified".

## Completion semantics

- Tick: `- [x]` plus `DONE:YYYY-MM-DD` at the end of the line.
- Untick: back to `- [ ]` and **remove** `DONE:` (including the space before it, so no
  double spaces remain).
- Done items are hidden on the board by default (there is a switch). The completion date
  lives only in `DONE:`; never touch `DDL:`.

## Blocked (`[-]`)

Not "cancelled" but "not moving right now": waiting on input, on scheduling, on energy.
It stays in the file (hidden by default) because "blocked for three months" is itself
information.

## Do not

| Do not | Why |
| --- | --- |
| change an existing ID | external notes and `^T-xxx` block references break |
| put order numbers at the end of lines | one drag rewrites dozens of lines, diffs explode |
| reorder lines to express priority | priority is a field (`#P1`), not a position |
| use `📅`, `【P1】`, `➕` style markers | they are hard to type and hard to grep |
| mix several projects in one file | project = file; mixing loses the grouping |
