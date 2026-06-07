# KEEL-3 — Acceptance Criteria gate

## Context
Second dogfood ticket. Adds a deterministic gate: a feature spec must declare a
non-empty "Acceptance Criteria" section, or CI blocks. This is the prerequisite for
the AI/human review step (KEEL-4) — you can only verify objectives written down.

## Plan
- `src/emkeel/gates/check_acceptance_criteria.py` — the gate.
- `tests/test_check_acceptance_criteria.py` — tests, incl. `main()` end-to-end
  (the lesson from KEEL-2: test behavior, not just helpers).
- `.github/workflows/ci.yml` — new step running the gate on PRs.

## Acceptance Criteria
- A feature PR whose spec lacks a non-empty "Acceptance Criteria" section fails CI.
- A feature PR whose spec has the section with content passes.
- Non-feature branches (chore/fix/docs) are not required to have it.
- This very PR (`feat/KEEL-3`) carries this section, so the gate validates itself.

## Anti-regression
- Tests cover: section present, absent, empty (heading only), case-insensitive
  heading, and `main()` exit codes for each path.
