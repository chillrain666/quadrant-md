# Contributing

Thanks for taking a look. A few conventions keep this repo readable.

## Language

- **Everything in the repository is English**: code, comments, docstrings, UI strings,
  commit messages, issues and pull requests.
- The only intentional Chinese is the **language pack** (`app/web/src/i18n.ts`), the
  Chinese README (`README.zh-CN.md`) and the trigger keywords in
  `skill/quadrant/SKILL.md` (so Chinese requests still route to the skill).

## Commits

Conventional Commits, English subjects, imperative mood:

```
feat: drag onto a tab to tag or move a task
fix(writer): keep CRLF when appending to a CRLF file
docs: explain the ordering model
```

Keep each commit focused; no merge commits from `main` — rebase instead.

## Code

- Python 3.10+, no formatter required, but keep the existing style (docstrings explain
  *why*, not *what*).
- The frontend has no third-party UI or drag-and-drop library; keep it that way unless
  there is a strong reason.
- Anything that **mutates files** needs assertions: run `cd app && uv run python run_tests.py`.
