# KEEL-68 — Auto-clean local emkeel leftovers after shipping; doctor measures wiring vs origin

## Context
After ship_update/ship_set ship the wiring to main (isolated worktree), the emkeel files written by
older `emkeel update` runs still sat uncommitted in the user's working tree — pending, and at risk of
being bundled into their own commits. The tool must clean those automatically, touching only its own
files. And after cleaning, a feature branch is "behind" main's wiring, which would nag-loop if drift
were measured locally.

## Plan
- `src/emkeel/ship.py` — `_clean_local(target)`: remove the dirty emkeel-generated files (only the
  `_files` set, only when content == the generated template; never product work, user specs/records,
  or hand-edits). Called by ship_update/ship_set after a successful ship.
- `src/emkeel/update.py` — `wiring_drift` measures against origin/<default> (governance source of
  truth) with a local fallback, so a feature branch behind main doesn't show as drift.
- Tests (real git). Bump 0.1.54.

## Acceptance Criteria
- After `emkeel update`, the emkeel files are shipped + removed from the working tree; the user's
  product work, their own emkeel-governance specs/records, and any hand-edited emkeel file are untouched.
- wiring_drift reflects origin/<default>: clean when origin is current (even on a stale feature branch),
  flagged when origin is behind; local fallback when there's no remote.

## Anti-regression
- Tests: _clean_local reverts/removes only emkeel leftovers + leaves product/user-artifacts/hand-edits;
  wiring_drift clean-vs-origin-current and stale-vs-origin-behind; existing no-remote tests still pass.
