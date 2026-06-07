# KEEL-2 — Gate: plan-presence for features

## Context
First dogfood ticket: the first real change to run through Emkeel's loop
(branch → PR → CI gates → merge). Adds the second deterministic gate.

## Plan
- `src/emkeel/gates/check_plan_present.py` — the gate: a `feat/` branch requires
  `emkeel-governance/specs/<KEY>.md`; other types don't.
- `tests/test_check_plan_present.py` — its test (test-on-fix from day 1).
- `.github/workflows/ci.yml` — a new step that runs the gate on PRs.

## Acceptance Criteria
- A feature PR (`feat/` branch) without its spec fails CI.
- A feature PR with its spec passes.
- Non-feature branches (chore/fix/docs) are not required to have one.
- This very PR (`feat/KEEL-2`) carries its spec, so the gate validates itself.

## Anti-regression
- Tests cover: feature requires spec, non-feature doesn't, and detecting a present spec.
