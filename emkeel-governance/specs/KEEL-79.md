# KEEL-79 — Anti-silent-drift gate: changing the north star needs a dedicated strategy lane

## Context
The approved `emkeel-governance/strategy/*.md` is the governed north star. Today any branch
(`feat/`/`fix/`/`chore/`/`docs/`) can edit or delete it inside an ordinary PR — so the code could quietly
bend the north to fit itself. Changing direction must be a deliberate act, on its own branch and ticket.

This is the sibling of `check_maint_scope` (which bounds *which* files the `emkeel-maint` lane may touch).
Here we bound *who* may touch `strategy/*.md`: only a `strategy/<TICKET>-slug` lane.

## Plan
- `src/emkeel/gates/check_strategy_change.py` — new gate. Reuses `check_maint_scope.changed_files(base)`
  (no duplicated diff) and `check_ticket_link.find_ticket_key`. Filters the diff to `.md` files under
  `EMKEEL_STRATEGY_DIR` (default `emkeel-governance/strategy`; ignores `.gitkeep`/non-md). If none →
  N/A (OK). If any → the branch must start with `strategy/` AND carry a ticket key → OK, else FAIL.
  Captures ADD/EDIT/DELETE (deleting the north is changing it). Not dormant-by-existence: the first
  creation of a strategy doc also goes through the lane. Config: `EMKEEL_STRATEGY_DIR`, `EMKEEL_BRANCH`,
  `EMKEEL_BASE_REF` (default `main`). stdlib only, exit 0/1.
- `.github/workflows/ci.yml` — add the gate step to the `gates` job (PR-only; needs the existing
  `fetch-depth: 0`).
- `src/emkeel/init.py` — same step in the scaffolded `_ci_yaml()` (governed repos get it on `emkeel
  update`); document the `strategy/<KEY-123>-slug` lane in the AGENTS.md template.
- Tests; bump 0.1.65.

## Invariants (don't break)
- The gate does NOT restrict the *other* files a `strategy/` branch carries (its ADR, spec, etc.). One
  direction only.
- `check_ticket_link`: a `strategy/ECO-20-…` branch already passes (it has a key) — unchanged.
- `check_plan_present`: `strategy/` is not in `FEATURE_PREFIXES` (only `feat/`/`feature/`) → it does not
  demand a spec for a strategy lane. Left as-is (a north-star change is governed by the doc + ADR + human
  gate, not a spec).
- The emkeel repo's own `strategy/` is empty → the gate is N/A there; its CI is not broken. This very PR
  is a `feat/` that touches no `strategy/*.md`, so the new gate returns N/A on itself.

## Acceptance Criteria
1. `feat/` editing a `strategy/*.md` → FAIL.
2. `strategy/KEEL-99-foo` editing a `strategy/*.md` → PASS.
3. A branch that touches no `strategy/*.md` → OK (N/A).
4. A change touching only `strategy/.gitkeep` or a non-md under `strategy/` → N/A (does not trigger).
5. DELETE of a `strategy/*.md` on a `feat/` branch → FAIL.
6. A `strategy/` branch WITHOUT a ticket key → FAIL (traceability).
7. `EMKEEL_STRATEGY_DIR` injectable, tested with fixtures (no hardcoded cwd).
8. Coverage maintained (≥85% branch / ≥90% line on changed files).
