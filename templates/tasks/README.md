# tasks · a plain-markdown todo directory

This is the whole "database": a pile of `.md` files. Sync it with Git, Syncthing,
iCloud or a USB stick; edit it in Obsidian, VSCode or vim. There are only a few rules.

## Directories are semantics

| Path | What it is | On the board? |
| --- | --- | --- |
| `1-active/**` | Work in progress; one file per project | ✅ the **only** source of the quadrants and Focus |
| `follow/` | Lists: shows, serials, books | ✅ own tab, no P/U, no counts |
| `4-someday.md` | "One day" items and ideas | ✅ own panel |
| `0-inbox.md` | Raw capture, not thought through yet | ❌ never shown |
| `2-notes/` | Long details | ❌ |
| `3-log/` | Timeline log, append only | ❌ |
| `5-archive/` | Finished projects | ❌ |
| files starting with `_`, `README.md` | templates / docs | ❌ |

## Task line syntax

Only a **flush-left** `- [ ]` starts a new task. Indented lines below it are that
task's details, kept verbatim:

```markdown
- [ ] T-261021-1 Task title #P1 #U2 #tag DDL:2026-11-05
      Detail line: belongs to the task above, deleted with it, searched too
```

| Piece | Meaning | Notes |
| --- | --- | --- |
| `- [ ]` / `- [x]` / `- [-]` | To do / Done / Blocked | three states, nothing else |
| `T-261021-1` | Globally unique ID | `T-` + `YYMMDD` + `-` + daily sequence; **never change it** |
| `#P1` `#P2` `#P3` | Importance (P1 = most) | the Y axis of the quadrants |
| `#U1` `#U2` `#U3` | Urgency (U1 = most) | the X axis |
| `#any-tag` | Search dimension, several allowed | CJK, capitals and `a/b` all work |
| `DDL:2026-11-05` | Due date | day precision; `DONE:` is added when you tick |
| `DONE:2026-10-21` | Completion date | added on tick, removed on untick |

**Quadrants are not stored**; they are `P × U` computed on the fly:

```
            U1 (most urgent)  U2        U3 (least urgent)
P1 (most)   Q1                Q2        Q2
P2          Q3                Q4        Q4
P3 (least)  Q3                Q4        Q4
```

The board draws a **3x3 grid** (one row per P, one column per U), because P and U each
have three levels; squeezing them into four cells throws information away.

## Three restraints

1. **Priority is a field, not a position**: changing it means changing one character,
   never moving paragraphs. (Board drag order lives in the app's `.order.json` and
   never enters markdown.)
2. **Capture is free**: vague or "someday" items go to `0-inbox.md` and stay unsorted.
3. **The weekly review is the only ritual**: completion tracking, moving things on and
   archiving all happen there.

## Write-back rules for agents (important)

- **Touch only the line you meant to touch**: line order, other lines, indented
  details and newline style (CRLF/LF, per file) stay exactly as they are.
- Creating a task means **appending one line** at the end of the target file, with an
  ID equal to "largest sequence used today across the tree + 1".
- Ticking means changing `[ ]` to `[x]` and adding `DONE:YYYY-MM-DD`; unticking is the
  reverse and removes `DONE:`.
- Drag order is **never written into markdown**; it is derived UI state.
