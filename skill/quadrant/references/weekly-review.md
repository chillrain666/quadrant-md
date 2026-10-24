# Weekly review (the only mandatory ritual)

Without a review this system turns into "another list of things I never did" within
three weeks. **Once a week, 15 minutes, five steps.** Do not invent a sixth.

## 1. Count (5 minutes)

```bash
# completed this week (look at the DONE: dates)
grep -rn "DONE:$(date +%Y-%m-%d)" tasks/1-active | wc -l
# overdue and still open
grep -rn "DDL:" tasks/1-active | grep -v "DONE:"
```

Answer three questions in `3-log/<year>-W<week>.md`:

- What actually moved this week? (**finished things only**, not "in progress")
- What is stuck, and on whom?
- Is anything "untouched for three weeks"?

## 2. Clear the inbox (3 minutes)

Go through `0-inbox.md` line by line; each line has exactly one destination:

| Destination | When |
| --- | --- |
| delete | not important, never going to happen |
| -> `1-active/` | this week or next week |
| -> `4-someday.md` | want to, but not now |
| stay in inbox | not decided yet — allowed, but not for more than four weeks |

After moving lines, delete them from the inbox (**this is the only moment inbox content
may be removed**).

## 3. Pull from someday (2 minutes)

Scan `4-someday.md`:

- clearly "next month" -> move to `1-active/`, add P/U
- clearly not wanted any more -> delete
- everything else stays

## 4. Archive (2 minutes)

A project file with only completed tasks, or a project that is over -> move the whole
file to `5-archive/<year>/`. Archived files leave the board automatically.

## 5. Set next week's Focus (3 minutes)

Tag **at most five** tasks with `#TopN` (`N` is the literal letter):

- Order of preference: **Q1 (P1U1) first, then Q2 (P1U2/U3)**; keep at least one Q2 slot
- Remove the tag from anything finished this week; Focus does not expire tags for you
- The Focus panel sorts "overdue -> today -> P1U1 -> ..." automatically; no manual order

## Review output

Write it to `3-log/`; format is free, but it must have three sections: what was done /
where it is stuck / what to follow next week. Logs are append-only — do not edit last
week's entry.

## How the agent helps

When the user says "let's do a review / how was this week":

1. Read only first: summarise the numbers (completed, overdue, inbox size, new tasks)
2. List every inbox line with a suggested destination and **wait for the user** before
   touching files
3. Archiving, pulling from someday, tagging `#TopN`: **propose the list, then execute**
4. Write the review into `3-log/` using the real current date
