# KEEL-44 — Finish the adopt: push + PR + auto-merge (adoption PR only)

## Context
Installing emkeel ends on a local adopt branch; the user then has to push, open a PR and merge
it by hand. For the **adoption PR specifically** that friction is unnecessary. Normal project
changes must keep the human-approved merge (the whole point of the gates).

## Plan
- `src/emkeel/connect.py` — after protection + secrets, if on a non-default branch, offer (opt-in,
  default No) to push HEAD, `gh pr create --fill`, and `gh pr merge --auto --squash` (GitHub's
  native auto-merge → merges WHEN the gates pass + approvals are met). Push has a timeout + a clear
  manual fallback (pre-push hooks can hang). `tests/test_connect.py`. Bump 0.1.28.

## Acceptance Criteria
- On a non-default branch, connect offers to push + open a PR + enable auto-merge; accepting runs
  those gh/git commands; auto-merge uses `--auto` (does NOT bypass the gates).
- On the default branch, the finish-adopt step is not offered.
- A push timeout/failure prints the exact manual recovery commands.

## Anti-regression
- Tests cover: current_branch, push timeout fallback, the full finish-adopt flow (push/pr/merge),
  and that the step is skipped on the default branch.
