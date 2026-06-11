# KEEL-70 — Don't open a PR for an emkeel.toml change that is only the version stamp

## Context
Verified in em-ecosystem: `emkeel update` opened PR #376 changing ONLY `generated_with`
(0.1.54→0.1.55) — a stamp-only no-op that recurs on every `pipx upgrade`. The stamp is vestigial
(nothing reads it; doctor measures drift excluding emkeel.toml), so these PRs are pure noise.

## Plan
- `src/emkeel/ship.py` — in `_ship_via_worktree`, after `mutate`, if emkeel.toml differs from HEAD
  only by the `generated_with` line (`_strip_stamp`), revert it → the change is dropped → "nothing to
  ship". `ship_set` (a real value change) still ships. `tests/test_ship.py`. Bump 0.1.56.

## Acceptance Criteria
- `emkeel update` when origin/<default> differs only by the emkeel.toml stamp opens NO PR.
- A real wiring change still ships; `emkeel set` (value change) still ships.

## Anti-regression
- Tests: ship_update with a stamp-only origin diff → no PR; isolate/refresh + nothing-when-current still pass.
