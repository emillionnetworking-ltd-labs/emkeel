# KEEL-48 — git push inherits the terminal (no silent hang)

## Context
In `connect` (finish-adopt) and `eject --remote`, `git push` ran with captured stdout/stdin, so a
long pre-push hook or an SSH passphrase / credential prompt hung the wizard invisibly (looked
frozen). Discovered on em-ecosystem (pre-push hooks).

## Plan
- `src/emkeel/connect.py` + `src/emkeel/uninstall.py` — give `_run` a `capture` flag; push with
  `capture=False` so git's output and any prompt are visible and answerable, and Ctrl-C cancels
  cleanly (caught → manual fallback). Print a "Pushing…" note first. `tests/`. Bump 0.1.32.

## Acceptance Criteria
- The push during finish-adopt / eject --remote shows git's output (not captured) and a Ctrl-C
  ends it gracefully with a manual-command fallback (no traceback, no silent hang).

## Anti-regression
- Tests cover do_push timeout fallback and the finish-adopt / remote_cleanup command sequences
  (run-fakes accept the new `capture` kwarg).
