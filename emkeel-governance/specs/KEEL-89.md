# KEEL-89 — Generic governed-process engine (state machine) in emkeel; /strategy as first adopter

Strategy: none (foundational governance tooling — not a feature serving a product strategy)

## Context
Skills (`/strategy`, `/launch-satellite`) are **prose + an exit gate** → an obligatory step can be silently
skipped and the final artifact still passes. The 6-step lifecycle doesn't have this problem because it's a
**state machine**: the engine refuses to advance without the prerequisite. This brings that mechanism,
**generic and distributable**, into emkeel (inherited by every governed repo via `pip install emkeel`).

## Plan
- `src/emkeel/process.py` — the **generic engine** (library): `ProcessSchema`/`Step` (data a skill
  declares), pure `evaluate_prereq` + `advance` (raise `PrereqError` on refusal — skipping impossible),
  state as **JSON on disk** under an `fcntl.flock` lock (`_ProcessLock`, exclusive/shared, `LockTimeout`).
  Stdlib-only (zero-dep): JSON not PyYAML. Reuses the lifecycle pattern (`_state_machine.py`).
- `src/emkeel/strategy.py` — **first adopter**: `strategy_process()` declares the schema
  `scaffolded → researched → proposed → critiqued → checked → presented → approved`; `emkeel strategy
  advance <step> <topic> [--set k=v]` / `status <topic>` drive the engine. The `researched` gate **requires
  provenance** (≥1 verifiable external source OR `internal_only=true`) → subsumes the research gate;
  `approved` requires a recorded human decision (`approved_by`).
- `emkeel-governance/adr/0005-governed-process-engine.md`. Bump 0.1.75.

## Invariants
- GENERIC and in emkeel (reusable by installation, not tied to any product); reuses the proven lifecycle
  pattern (no reinvention); lib + thin CLI; zero-dependency stdlib.
- The `/strategy` prose in em-ecosystem (calling `emkeel strategy advance <step>`) is a **follow-on** — not
  touched here; the engine is tested against the `/strategy` schema in this PR.

## Acceptance Criteria
1. Advancing into a step without its prerequisite (skipping) is REFUSED (`PrereqError`); in order, it
   advances and records the step's evidence.
2. State persists on disk and is the source of truth; writes are exclusive-lock-guarded (a second
   exclusive lock times out; shared locks coexist); garbage state → `StateParseError`.
3. The engine is generic — an arbitrary schema works; nothing is hardcoded to `/strategy`.
4. `/strategy` schema: `approved` is unreachable by skipping; `researched` requires provenance (URL/repo
   file:line OR `internal_only`); `checked` requires a recorded pass; `approved` requires `approved_by`.
5. The `emkeel strategy advance` / `status` CLI drives the engine on disk (refusal surfaces too).

## Follow-on
- Update the `/strategy` skill prose in em-ecosystem to call `emkeel strategy advance <step>` at each step.
- Other skills (`/launch-satellite`) declare their own `ProcessSchema` to become non-skippable.
