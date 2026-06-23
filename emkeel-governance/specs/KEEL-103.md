# KEEL-103 — Anti-regression: a critical change must ship an integration test

Strategy: none (governance/CI tooling — a gate + the agent contract, not a product feature)

## Context
The KEEL-93/94 incident: the credential-isolation change broke `emkeel jira create` (it depended on
direnv) and **no test caught it** — coverage was unit-only (no end-to-end test of the creds→create flow)
and the design wasn't robust (it relied on an optional tool). This makes "don't break something else in
silence" enforceable + a written discipline.

## Plan
1. **`check_critical_integration`** (new CI gate, deterministic, diff-based): an explicit MANIFEST of
   critical/cross-cutting surfaces — `jira.py` (creds), `isolation.py` (isolation + guard), `init.py` /
   `update.py` / `ship.py` (distribution + the agent contract), and `gates/` (any gate). If a PR's diff
   touches a critical surface it MUST also add/change a test under `tests/integration/`; else FAIL. N/A
   otherwise. Like `check_plan_present` requires a spec on `feat/`, this requires an e2e test on a critical
   change. Wired into `ci.yml` + the scaffolded `_ci_yaml` (runs inside the `gates` required check).
2. **`tests/integration/`** — created and seeded with the creds→`emkeel jira create` flow WITHOUT direnv
   (the KEEL-102 flow), the pattern the gate enforces: scoped `.env` only → create succeeds; cross-project
   still blocked; no creds → loud fail.
3. **Agent contract (`_agents_md`)** — "Don't break something else in silence": critical change → add an
   integration test; critical infra must be self-sufficient (no optional-tool deps like direnv); never
   hide failures with `2>/dev/null`, verify the cwd/destination before writing (the `.env`-clobber lesson).

## Acceptance Criteria
1. The gate FAILS when a critical surface is touched without a `tests/integration/` change, and PASSES when
   one is added; N/A when no critical surface is touched.
2. The critical-surface manifest is explicit and unit-tested (each listed surface is `is_critical`; the gate
   file itself is critical).
3. `tests/integration/` exists with the creds→create-without-direnv flow (create succeeds from the scoped
   `.env`; cross-project blocked; no-creds loud-fail).
4. The distributed CI (`_ci_yaml`) and the agent contract carry the rule. Bump 0.1.87; all tests pass.
