# Summaries: daily standup and weekly report

Two different artefacts, both built **from evidence only**:

- **Daily** — what moved today, what is blocked, what is next. 5–8 lines.
- **Weekly** — what shipped this week, what slipped, where the time went, next week's
  Focus. Half a page.

The rule for both: **a task counts as done only if it carries `DONE:<date>`**. No
"basically finished", no memory-based claims. If the user insists something was done
but the file says otherwise, write it under `Notes` and ask, do not silently promote it.

## 1. Gather the evidence

```bash
# --- daily (today = 2026-10-21) ---------------------------------------------
grep -rn "DONE:2026-10-21" tasks/1-active tasks/4-someday.md tasks/follow

# tasks created today (the date is in the ID)
grep -rn "T-261021-" tasks/1-active | grep -v DONE:

# blocked items
grep -rn "^- \[-\]" tasks/1-active

# log entries written today
ls tasks/3-log/*/ 2>/dev/null | tail -5
```

```bash
# --- weekly --------------------------------------------------------------
# every DONE in the window (replace with the real dates)
grep -rn "DONE:2026-10-19\|DONE:2026-10-2[0-5]" tasks/1-active

# what changed in the data repo itself (the user's own notes)
git -C tasks log --oneline --since=2026-10-19 --until=2026-10-26
```

If the panel is running, `GET /api/focus` and `GET /api/tasks?status=done&include_done=true`
give the same data with labels resolved; use whichever is cheaper.

## 2. Daily template

```markdown
# 2026-10-21

## Done
- T-261021-3 Skim the FastAPI dependency-injection docs

## In progress
- T-261021-2 Draw the RAG retrieval pipeline (half done)

## Blocked
- T-261021-11 Waiting for requirements — since 10-19

## Next
- T-261021-8 Login edge cases (DDL tomorrow)
```

Rules:
- `Done` is **only** `DONE:<today>` items; quote the ID so it can be checked.
- `In progress` = files touched or comments added today, not "I thought about it".
- `Blocked` includes how long it has been blocked (compute from the ID date or the log).
- `Next` = tomorrow's `#TopN` or the nearest `DDL`; **do not invent priorities**.

## 3. Weekly template

```markdown
# 2026-W43 (10-19 → 10-25)

## Shipped
- 4 tasks closed (list IDs + one-line outcome)

## Slipped
- 2 tasks were due and are still open (list IDs + new DDL if any)

## Where the week went
- by project: work 6, study 3, life 2
- by quadrant: Q1 5, Q2 4, Q3 1, Q4 1

## Blocked / waiting
- T-... blocked since 10-19, owner: <who>

## Next week
- Focus (max 5): T-..., T-..., T-...
- One thing to drop: T-...
```

Computing the breakdowns: count `done` per `project` and per `quadrant` from the same
`DONE:` window. Counts are cheap; do not paste the whole task list.

## 4. Where the report goes

- **Daily**: `tasks/3-log/YYYY-MM/YYYY-MM-DD.md` (create the month folder if needed).
- **Weekly**: `tasks/3-log/YYYY-Www.md` (`2026-W43`).
- Append if the file exists; never rewrite yesterday's entry (logs are append-only).

If the user only wants it in chat, still offer to save it — a report nobody can find
later is not a report.

## 5. Tone and length

- Bullets, no prose. One line per item.
- Quantify: "4 tasks closed", "2 slipped", "blocked 6 days" — not "a lot".
- No praise, no filler ("great progress"). The user wants a mirror, not a coach.
- Write in the language the user asked in; keep task IDs and tags verbatim.

## 6. What not to do

| Do not | Why |
| --- | --- |
| list every open task | a report is a delta, not a backlog dump |
| mark something done without `DONE:` | the file is the source of truth |
| reorder or archive tasks while reporting | reporting is read-only unless asked |
| edit last week's log entry | logs are append-only |
| guess next week's priorities | ask, or mirror the existing `#TopN` tags |
