# KEEL-39 — jira-transition warns when secrets are missing

## Context
If the user forgets to set the Jira secrets, the post-merge auto-transition would fail
cryptically (or silently). It should clearly tell the user — on every merge — that auto-close
is off and how to fix it, without failing the merge (it's non-blocking).

## Plan
- `src/emkeel/jira.py` — add `secrets_present()`; in `main()`, if the Jira secrets are missing,
  print a GitHub Actions `::warning::` (auto-close OFF — add secrets at <link>) and skip
  gracefully (exit 0). Reaches existing repos via the version-pinned `pip install`. `tests/test_jira.py`.
  Bump 0.1.23. (The "gates not required" warning is handled by `emkeel doctor` — CI lacks admin to check it.)

## Acceptance Criteria
- With Jira secrets missing, `emkeel.jira` prints a `::warning::` with the secrets link and exits 0 (non-blocking).
- With secrets present, it proceeds to transition as before.

## Anti-regression
- Tests cover `secrets_present` (set/unset) and that `main` warns + skips (exit 0) without secrets.
