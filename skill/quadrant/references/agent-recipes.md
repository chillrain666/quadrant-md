# Agent recipes (user sentence -> exact action)

> All examples assume the data directory is `tasks/` (otherwise use `TASKS_ROOT`).
> Principle: **append or edit one line**, never rewrite a file; read it back afterwards.

## Recipe 1: capture something not thought through

> "Note that I want to try a two-week review cycle"

```bash
printf '%s\n' '- Try a two-week review cycle' >> tasks/0-inbox.md
```

No ID, no P/U, no date. **Do not** classify it or move it to `1-active/`.

## Recipe 2: add a real task

> "Turn the API error codes into a table before Friday"

1. Pick the file: a known project -> `1-active/<group>/<project>.md`; no home ->
   `1-active/life/chores/chores.md`; a new project -> create the file (heading first,
   then a blank line).
2. Compute the next ID (see `md-conventions.md`, or run `writer.next_id()` from `app/`).
3. Append:

```markdown
- [ ] T-261021-18 Turn the API error codes into a table #P2 #U1 #work DDL:2026-10-23
```

Defaults for P/U: a hard, near deadline -> `#U1`; moves a long-term goal -> `#P1`;
a quick errand -> `#P3 #U1`. **If the user did not say, do not guess both axes.**

## Recipe 3: complete / un-complete

```
- [ ] T-261021-18 Turn the API error codes into a table #P2 #U1 ... DDL:2026-10-23
```
-> done (today is 2026-10-23):
```
- [x] T-261021-18 Turn the API error codes into a table #P2 #U1 ... DDL:2026-10-23 DONE:2026-10-23
```
-> undo: put the space back and **remove** ` DONE:2026-10-23` (with the leading space).

Only these two spots change; `DDL:` stays.

## Recipe 4: change priority or due date

> "make this P1" / "move it to this weekend"

Replace only the `#P?` / `#U?` / `DDL:YYYY-MM-DD` tokens, leave every other character
alone.

## Recipe 5: block it

> "park this until they reply"

`[ ]` -> `[-]`, optionally add a tag such as `#blocked`. Do **not** delete the task and
do not move it elsewhere.

## Recipe 6: move it

> "later, not now" -> cut the whole line (with its details) to the end of `4-someday.md`
> "start this week" -> move it to the end of `1-active/<project>.md`
> "different project" -> move it to the end of the new file, leaving no blank line behind

**Move the line plus its indented details together.** The ID never changes: it is
identity, not location.

## Recipe 7: delete

> "drop this"

Delete the task line plus every indented line right after it. Do not touch neighbouring
tasks, and do not leave a blank line behind. Deletion is irreversible: if the text is
worth keeping, ask first whether to move it to someday.

## Recipe 8: watch list

> "found another show"

```markdown
- [ ] T-261021-19 Example Show F #shows
```
Goes in `watch/shows.md` (or `watch/<anything>.md`). No P/U, no DDL. Ticking adds
`DONE:`.

## Recipe 9: weekly review

See `weekly-review.md`.

## Recipe 10: run / fix the board

```bash
cd app && uv run python main.py               # http://127.0.0.1:8000
uv run python app/main.py --port 8010         # port already taken
```
A 404 or missing tasks -> check `tasksRoot` in `/api/meta` (see `panel.md`).

## Three checks before writing

1. Which **file and which line** am I changing? Can I change only that line?
2. Will this touch **someone else's line** (order, blank lines, newline style)?
3. Did I **read it back** and does it match (unique ID, `DONE` neither missing nor
   doubled)?
