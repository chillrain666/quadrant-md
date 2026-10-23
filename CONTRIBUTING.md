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

## Branches and history

`main` is the publishable line: it is always English, linear, and free of
"work in progress" noise. Everything else lives on local branches that are never
pushed.

| Branch | Where | What is allowed |
| --- | --- | --- |
| `main` | pushed | English only; squashed or focused commits; no WIP, no "fix typo" chains |
| `exp/<topic>` | local only | anything: broken states, Cyrillic commit messages, throwaway experiments |
| `wip/<topic>` | local only | a feature that is not ready but worth keeping |

Rules:

1. **Experiment locally, publish cleanly.** Work on `exp/<topic>`; when the result is
   worth publishing, collapse it into one reviewable commit on top of `main`.
2. **No experiment branches on the remote.** Do not push `exp/*` or `wip/*`; delete them
   when they are done (`git branch -D exp/foo`).
3. **Publishing is one deliberate step**: squash, write the final English message,
   then push. Never push a stream of intermediate commits.
4. **Do not rewrite public history casually.** If `main` has to be rewritten (for
   example to remove something that must not be there), take a mirror backup first,
   rewrite locally, verify `git log` and the trees, and only then
   `git push --force-with-lease`. Prefer fast-forward pushes.
5. **Commit messages describe the result, not the process.** No "translate X to
   English", "cleanup after the previous commit" or similar meta commits: fold that
   work into the commit it belongs to.

Publishing a squashed change:

```bash
# from exp/new-thing
 git switch main
 git merge --squash exp/new-thing
 git commit -m "feat(app): describe the result, not the steps"
 git push origin main
```

If the intermediate history must not appear at all (first release, or a cleanup that
should be invisible), rebuild the commit with `git commit-tree` and move the branch
over it — that is how the v1.0 line in this repository is kept as a single commit.

## Code

- Python 3.10+, no formatter required, but keep the existing style (docstrings explain
  *why*, not *what*).
- The frontend has no third-party UI or drag-and-drop library; keep it that way unless
  there is a strong reason.
- Anything that **mutates files** needs assertions: run `cd app && uv run python run_tests.py`.
