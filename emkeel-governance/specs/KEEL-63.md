# KEEL-63 — Strategy Layer 1: persisted artifact + check_strategy_link gate + AGENTS.md rule

## Context
The old framework had a great strategy ENGINE but the strategy lived only in chat and was never
referenced per-ticket → drift. Emkeel's fix is persistence + enforcement (not porting LangGraph):
a strategy artifact in the repo, referenced by feature specs, enforced by a gate. Generation
(the debate, Layer 2) stays OUT of the package (a skill/workflow writes the .md).

## Plan
- `src/emkeel/gates/check_strategy_link.py` — feature specs must declare `Strategy: <slug>` →
  existing `emkeel-governance/strategy/<slug>.md` (or `none`). DORMANT until the first strategy exists.
- `src/emkeel/init.py` — scaffold `emkeel-governance/strategy/.gitkeep`; wire the gate into the
  generated CI (`_ci_yaml`); add the Strategy rule to the generated AGENTS.md.
- `.github/workflows/ci.yml` — add the gate to emkeel's own CI (dogfood).
- Tests across the gate + init. Bump 0.1.49.

## Acceptance Criteria
- Once any `emkeel-governance/strategy/*.md` exists, a feature PR fails unless its spec declares a
  valid `Strategy:` link (or `none`); dormant (passes) when no strategy exists.
- New adoptions scaffold `strategy/`, wire the gate in CI, and document the rule in AGENTS.md.

## Anti-regression
- Tests: gate non-feature/dormant/missing-line/none/valid/unknown/no-spec; init scaffolds dir,
  CI includes the gate, AGENTS.md documents Strategy.
