# KEEL-65 — `emkeel update/set --ship <KEY>`: governance-respecting auto-ship

## Context
`emkeel update`/`set` leave refreshed files uncommitted; the operator then hand-does branch→commit
→push→PR→merge. Automate it WITHOUT bypassing governance (no direct push to main; the gates still run).

## Plan
- `src/emkeel/ship.py` — `ship(key, paths, target, run)`: chore/<KEY>-emkeel-update → commit only the
  given emkeel-managed paths → push (terminal-inherited) → PR → native auto-merge. `ship_key_from(argv)`.
  Reuses connect.py (do_push/do_pr_create/allow_auto_merge/do_auto_merge). Rejects a bad key; no-op when empty.
- `src/emkeel/update.py` + `src/emkeel/setcfg.py` — accept `--ship <KEY>`; ship the changed files.
- `src/emkeel/cli.py` — document the flag. Tests. Bump 0.1.51.

## Acceptance Criteria
- `emkeel update --ship KEEL-9` (with real changes) creates a chore branch, commits the changed
  files, pushes, opens a PR, and enables auto-merge (merges when the gates pass) — never pushes to main.
- `emkeel set jira-project ECO --ship KEEL-9` ships emkeel.toml the same way.
- Bad/missing key rejected; no-op when nothing changed.

## Anti-regression
- Tests: ship full-flow sequence, bad key, no-op; ship_key_from parsing; update/set route to ship.
