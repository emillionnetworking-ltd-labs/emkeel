# KEEL-49 — enable repo 'Allow auto-merge' before gh pr merge --auto

## Context
`gh pr merge --auto` fails with "Auto merge is not allowed for this repository" unless the repo
setting `allow_auto_merge` is on (seen on em-ecosystem). connect must enable it first.

## Plan
- `src/emkeel/connect.py` — `allow_auto_merge(repo)` (`gh api -X PATCH repos/{repo} -F
  allow_auto_merge=true`); call it right before `do_auto_merge` in finish-adopt. On auto-merge
  failure, print a clearer fallback (PR is open — merge when green, or enable the setting + retry).
  `tests/test_connect.py`. Bump 0.1.33.

## Acceptance Criteria
- finish-adopt enables the repo's allow_auto_merge setting before calling `gh pr merge --auto`.
- If auto-merge still can't be enabled, the message says the PR is open and how to finish it.

## Anti-regression
- Tests: allow_auto_merge issues the PATCH; the finish-adopt flow enables it before --auto.
