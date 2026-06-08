# KEEL-50 — emkeel sync (post-merge local cleanup)

## Context
After the adopt PR merges, the user is stranded on the (now-merged) adopt branch and must run
checkout + pull + branch -D by hand. Automate it into one safe command, and let finish-adopt
offer to wait for the merge and do it.

## Plan
- `src/emkeel/sync.py` — `emkeel sync`: checkout default branch, `git pull --ff-only` (inherits
  terminal), `git fetch --prune`, then delete local chore/feat/fix branches that are merged
  (`--merged`) OR whose upstream is `gone` (catches squash-merges). `wait_for_merge()` polls a
  PR's state. `src/emkeel/cli.py` dispatch `sync`.
- `src/emkeel/connect.py` — after auto-merge is on, offer to wait for the merge (Ctrl-C to skip)
  then sync; otherwise tell the user to run `emkeel sync`. `tests/`. Bump 0.1.34.

## Acceptance Criteria
- `emkeel sync` checks out the default branch, pulls, prunes, and removes branches merged or with
  a gone upstream (chore/feat/fix only; never the default).
- finish-adopt offers wait-and-sync when auto-merge is enabled; declining points to `emkeel sync`.
- `wait_for_merge` returns True when the PR is MERGED, False on timeout.

## Anti-regression
- Tests: default_branch, cleanable_branches (merged + gone), sync command sequence, wait_for_merge
  (polls to merged + times out).
