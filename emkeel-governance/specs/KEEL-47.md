# KEEL-47 — eject honest output + wizard resilience (no exit on recoverable errors)

## Context
Two bugs from testing: (1) `eject` printed "[removed]" + a list of "absent" items when nothing
local existed (misleading). (2) `setup` crashed and exited when the branch already existed
(`git checkout -b` fatal). Principle: no step should exit the wizard except a user cancel.

## Plan
- `src/emkeel/uninstall.py` — `_do_eject` lists only what was actually removed; if nothing, says
  "(no local Emkeel files to remove — already clean)". (Remote cleanup still runs.)
- `src/emkeel/wizard.py` — `branch_exists()`; if the adopt branch exists, offer **use another key /
  reuse the existing branch / cancel** (loop) instead of crashing; `run_setup` reuses the branch
  when chosen. On a hard `run_setup` failure, print a retry hint (don't crash silently).
- `src/emkeel/connect.py` — on create+push failure, print the manual command + how to resume.
- Audit of setup/connect/eject for exit-on-failure; recoverable errors now guide + continue.
  `tests/`. Bump 0.1.31.

## Acceptance Criteria
- `eject` with nothing local to remove says so honestly (no fake "removed" list).
- `setup` with an existing branch offers options (new key / reuse / cancel) and does not exit.
- create+push failure in connect prints the manual command and how to resume.

## Anti-regression
- Tests: eject nothing-to-remove; wizard branch-exists → new key; branch-exists → reuse.
