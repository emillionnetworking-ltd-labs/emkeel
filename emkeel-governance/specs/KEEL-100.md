# KEEL-100 — /strategy runs through the governed-process engine + a non-skippable CI gate

Strategy: none (governance tooling — the skill + a CI gate, not a product feature)

## Context
The process engine (`process.py`) and the `/strategy` schema (`strategy.py`: scaffolded → researched →
proposed → critiqued → checked → presented → approved, with the `_researched_provenance` gate) already
exist and are tested. The gap: the DISTRIBUTED skill `_strategy_skill()` (in `init.py`) still only called
`new`/`check` — it didn't drive the engine — and no CI gate read the `<topic>.process.json`. So an agent
could skip a step (notably the web research) and still merge a strategy doc.

## Plan (cable the existing pieces; don't rebuild them)
1. **`_strategy_skill()`** — rewrite the distributed skill to DRIVE the engine: after each step's work,
   `emkeel strategy advance <step> <topic> --set <evidence>`. At `researched`, record the real sources, or
   declare `internal_only=true` EXPLICITLY when the topic has no market dimension (never skip the web
   silently). Removed the "(No web access? …)" escape hatch. Commit the `<topic>.process.json` with the doc.
2. **`check_strategy_process`** (new CI gate) — when a PR touches `emkeel-governance/strategy/<topic>.md`,
   the committed `<topic>.process.json` must exist, have reached at least `checked` (every step up to it
   done), and its `researched` step must carry provenance (reuses `_researched_provenance`). Else FAIL.
   N/A when the diff touches no strategy doc. Wired into `ci.yml` + the scaffolded `_ci_yaml` (PR-only,
   `fetch-depth: 0`), so it runs for real like the other gates.

## Acceptance Criteria
1. The distributed skill drives `emkeel strategy advance` for all seven steps; the no-web escape hatch is
   gone; it commits the `<topic>.process.json`.
2. `check_strategy_process` PASSES a strategy doc whose `<topic>.process.json` reached `checked` with
   research provenance (a real source or `internal_only=true`); FAILS when the process.json is missing,
   hasn't reached `checked`, has no provenance, or is unparseable.
3. The gate is wired into the repo's CI and the generated CI; N/A when no strategy doc changed.
4. Bump 0.1.85; all tests pass.
