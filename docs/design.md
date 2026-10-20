# Design notes: why it looks like this

> This explains the trade-offs, not the usage. Usage lives in `README.md`; the agent
> handbook is `skill/quadrant/SKILL.md`.

## 1. Why markdown, not SQLite or a cloud service

A todo list is **a bag of state**, not relational data. Markdown gives us:

- **Readability**: no network, no account, and the files still open in a text editor ten
  years from now.
- **Diffability**: `git diff` shows what actually changed this week; a cloud service
  cannot.
- **Portability**: switching tools means switching a parser, not exporting data.
- **One interface for humans and agents**: an agent needs no API and no OAuth; it only
  needs to edit one line of text.

Cost: no transactions, no indexes, full scans. At a few hundred tasks this is
milliseconds. Revisit at a few thousand.

## 2. Why priority is a "field", not a "position"

Order cannot express two dimensions (importance and urgency), nor "these two are equally
important". Once priority *is* position, changing it means moving paragraphs: a red diff,
and a hand that slips.

So: **priority is `#P1` / `#U1` tags, and position only means "what I want to look at
first"**. They are stored separately:

- `#P1`~`#P3`: importance (the Y axis)
- `#U1`~`#U3`: urgency (the X axis)
- drag order: derived UI state (`.order.json`), **never in markdown**

## 3. Why 3×3, not four quadrants

The classic Eisenhower matrix cuts each axis into "high / low" and gives four cells. In
practice you need three levels (very / medium / not really); compressing that into two
forces you to stuff "medium" into one side arbitrarily.

Three levels per axis gives **nine cells**, and a 3×3 grid still reads well (one row per
P, one column per U). The classic four-quadrant view is still available from the grouping
dropdown.

## 4. Why four tracks

They are all "todos" but their semantics differ, and mixing them pollutes everything:

| Track | Meaning | P/U? | DDL? |
| --- | --- | --- | --- |
| `1-active/` | work in progress | yes | optional |
| `watch/` | lists (shows, books, serials) | no | no |
| `4-someday.md` | one day / ideas | no | no |
| `0-inbox.md` | not thought through | no | no |

Tagging a show with P1U1 is absurd; ranking an inbox idea is self-deception. Split, and
each panel handles exactly one kind of thing, with counts that do not interfere.

**The inbox is deliberately invisible**: the biggest enemy of capture is starting to
tidy.

## 5. Ordering: one global total order

- Every task has a `rank` (float).
- Without a saved order, the rank is derived from the ID (= creation order), so **the
  initial state is already sensible**.
- Dragging writes only the dragged task's new rank (`{"T-261021-3": 2.5}`); nothing else
  takes space.
- Drop semantics: **flush against the anchor**. When inserting before/after task `C`, the
  neighbours used are the *global* previous/next, not the ones visible in the view.

The last point matters: tasks hidden by the current filters are skipped, so after a drop
the moved task always sits flush against `C` and never slips between invisible entries.
The price is that it "jumps over" hidden tasks — which is exactly what was wanted.

**Honest limitation**: cross-view dragging can only guarantee that the relative order of
*tasks that were not dragged* stays the same. It is mathematically impossible to drag two
items in view A without changing their relation to a third item in view B.

## 6. Write-back rule: touch only the line that changed

- Original bytes are captured before writing; after writing the file is re-parsed and
  compared. On mismatch, the original bytes are **restored**.
- Newline style is **preserved per file** (a single library may mix CRLF and LF).
- Create = append to the end of the file, never insert in the middle.
- Delete = the task line plus its indented details, leaving no blank line behind.

This is what lets "human edits the file" and "the board writes back" coexist.

## 7. Synonyms: many names for one concept

`synonyms.json` holds groups of equivalent terms (case-insensitive, any number of terms):

```json
{ "groups": [["TopN", "focus"], ["someday", "later", "one-day"]] }
```

It applies to search, tag filters, Focus selection (`#focus` counts too) and tag merging.
Deleting the file degrades gracefully to "case-insensitive only".

## 8. Known trade-offs

| Trade-off | Why |
| --- | --- |
| Full scan, no index | milliseconds below a few hundred tasks; do not over-engineer |
| Single user, single machine | multi-user needs locking and merging; markdown is not built for that |
| No UI framework | small bundle, full control; cost is writing the components |
| Order files live next to the app, not the data | the data directory must be copyable on its own; order is reproducible |
| No reminders | reminders belong to a calendar or the OS; a markdown file never rings |
