# KEEL-45 — eject --remote: finish the un-govern on GitHub

## Context
`emkeel eject` only removes files locally; the user then has to commit, push and clean GitHub by
hand (and removing the gates workflow inside a PR deadlocks against the required check). This is
the mirror image of `emkeel connect` and should be automatable.

## Plan
- `src/emkeel/uninstall.py` — add `--remote`: after the local removal, **drop branch protection
  first** (so the missing gates check can't block), then `git add` only Emkeel's deletions +
  commit + push (timeout + manual fallback), then `gh secret delete` the Jira secrets. Repo is
  read from the git remote (emkeel.toml is already gone). gh missing/unauth → skip with a note.
  `tests/test_uninstall.py`. Bump 0.1.29.

## Acceptance Criteria
- `emkeel eject --purge --yes --remote` removes branch protection, commits + pushes the removal,
  and deletes the Jira secrets on GitHub.
- It stages only Emkeel's deleted paths (never the user's other files).
- Dry-run (no --yes) only previews; without gh it skips the remote step with a clear message.

## Anti-regression
- Tests cover: repo_from_git, remote_cleanup command sequence, and the push-timeout fallback.
