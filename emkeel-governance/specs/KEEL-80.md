# KEEL-80 — check_strategy_alignment: a feature serving a strategy must acknowledge how it aligns

## Context
`check_strategy_link` makes a feature spec point at its north star (`Strategy: <area>`). But an agent can
put the pointer and still build something the strategy forbids — semantic conformance is only caught by the
human at the PR. This narrows that gap: the spec must carry an `## Alignment` section that explicitly
acknowledges which north-star decisions/constraints the feature implements or touches. The gate is purely
SYNTACTIC — it requires the section to exist and be non-empty; the truth of the content stays with the
human (validating semantics would be AI judging AI, which violates adopt-and-thin).

## Plan
- `src/emkeel/gates/check_strategy_alignment.py` — new gate. Feature branches only (`spec_required`).
  Dormant until a strategy exists under `EMKEEL_STRATEGY_DIR` (same criterion as `check_strategy_link` —
  protects emkeel itself and strategy-less repos). Locates the spec (`find_ticket_key`/`spec_path_for`)
  and reads its link (`strategy_link`): missing spec / missing link / no ticket key → OK here (the sibling
  gate owns that FAIL); `Strategy: none` → OK (standalone); a real `<area>` → requires a non-empty
  `## Alignment` section, else FAIL. Config: `EMKEEL_STRATEGY_DIR` / `EMKEEL_SPECS_DIR` / `EMKEEL_BRANCH`.
- `check_acceptance_criteria.py` — generalize the section detector to `has_section(text, name)`;
  `has_acceptance_criteria` now delegates to it (behavior unchanged). The new gate reuses `has_section`.
- `.github/workflows/ci.yml` + `init.py _ci_yaml()` — add the gate step (PR-only).
- `init.py` AGENTS.md template — document the `## Alignment` requirement.
- Tests; bump 0.1.66.

## Invariants (don't break)
- `check_acceptance_criteria` behavior is unchanged (its tests stay green); only its internal detector is
  generalized and reused.
- Dormant when no strategy exists: emkeel's own `strategy/` is empty, so this very PR's spec needs no
  `## Alignment` and the gate returns N/A on itself — CI not self-blocked.
- No semantic validation: the gate only checks the section exists and has content.

## Acceptance Criteria
1. A feature spec with `Strategy: auth` and NO Alignment section (≥1 strategy exists) → FAIL.
2. A feature spec with `Strategy: auth` and an Alignment section with content → PASS.
3. A feature spec with `Strategy: auth` and an EMPTY Alignment heading → FAIL.
4. A feature spec with `Strategy: none` → OK (N/A) even without Alignment.
5. No strategies in the repo (empty dir) → dormant → OK (N/A) even without Alignment.
6. A non-feature branch (chore/fix/docs) → OK (N/A).
7. `EMKEEL_STRATEGY_DIR` / `EMKEEL_SPECS_DIR` injectable, tested with fixtures.
8. `check_acceptance_criteria` stays green (shared helper).
9. Coverage maintained (≥85% branch / ≥90% line on changed files).
