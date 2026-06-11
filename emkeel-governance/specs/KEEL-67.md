# KEEL-67 — Ship via an isolated git worktree (never touch the user's working tree)

## Context
ship operated in the main working tree, so it refused whenever the user had unrelated work in
progress (e.g. nexacore-api/report) → maintenance blocked, files left pending. A real repo always
has product work in flight, so this was unusable.

## Plan
- `src/emkeel/ship.py` — `_ship_via_worktree(mutate, …)`: `git worktree add` at origin/<default>,
  run `mutate(worktree)`, commit only the emkeel changes, push `emkeel-maint/<ver>-<sha>`, PR
  (`gh -R/--head/--base`), native auto-merge, then `worktree remove`. The working tree is untouched.
  `ship_update` (apply in the worktree) and `ship_set` (change a field in the worktree).
- `src/emkeel/update.py` + `setcfg.py` — default → ship via worktree; `--no-ship` → refresh the local tree.
- Tests (real git + faked gh). Bump 0.1.53.

## Acceptance Criteria
- `emkeel update` ships the wiring refresh through an emkeel-maint PR WITHOUT touching the working
  tree — the user's in-progress product files are left untouched + uncommitted.
- Nothing to ship when origin/<default> is already current.
- `--no-ship` still refreshes the local tree for manual commit.

## Anti-regression
- Tests: worktree ship isolates the working tree + refreshes only emkeel files; no-op when current;
  default-branch detection; update/set route to ship_update/ship_set vs --no-ship local.
