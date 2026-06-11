# KEEL-74 — check_strategy_quality gate: a strategy doc without sources can't merge

## Context
The hard half of Layer 2's anti-hallucination. The skill guides grounded research; this gate is the
computed fact: a strategy with an unsourced option (or a missing section) fails the build.

## Plan
- `src/emkeel/gates/check_strategy_quality.py` — runs `emkeel strategy` lint over all
  emkeel-governance/strategy/*.md (via `_do_check`); 0 if clean/none, 1 if any fails. Dormant when none.
- `src/emkeel/init.py` (`_ci_yaml`) + `.github/workflows/ci.yml` — wire the gate (PR-only). Tests. Bump 0.1.60.

## Acceptance Criteria
- On a PR, a strategy doc with an option lacking a Source (or a missing section) fails CI; a grounded
  + complete strategy passes; no strategy docs → dormant (pass). New adoptions wire the gate.

## Anti-regression
- Tests: gate dormant/pass-grounded/fail-ungrounded; generated CI includes check_strategy_quality.
