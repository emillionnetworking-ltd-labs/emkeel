# KEEL-35 — Wizard UX: no trial, cancel, detect existing

## Context
Real testing of `emkeel setup` surfaced three UX problems: the trial-vs-real choice is
confusing (the "trial" flashes by and isn't tangible), there's no way to cancel/exit a menu,
and re-running over an already-set-up repo silently scaffolds again.

## Plan
- `src/emkeel/wizard.py` — remove the trial/real question (the wizard just does the setup;
  undo is `emkeel eject`). Add a **Cancel** option (`c`/`q`) to every menu + **Enter = first
  option**. Detect an existing install (`emkeel.toml` present) and refuse to re-run (point to
  `emkeel eject`).
- `tests/test_wizard.py`; README note. Bump 0.1.19.

## Acceptance Criteria
- The wizard no longer asks "trial or real"; it does the setup directly.
- Every menu accepts `c` (cancel → exit cleanly, nothing changed) and Enter (→ first/default option).
- If `emkeel.toml` already exists, the wizard refuses to run and points to `emkeel eject` (no prompts).
- Cancelling before the final confirm changes nothing.

## Anti-regression
- Tests cover: choice default + cancel, cancel at the first menu (nothing written), existing-install
  detection (no prompt), and the normal flow still scaffolds.
