# KEEL-114 — /strategy reality gate: a `validated` step that proves a strategy was tried, not just processed

Strategy: none

## Context
`/strategy` drives a non-skippable governed process (scaffolded → researched → proposed → critiqued →
checked → presented → approved). Every step proves the process *happened and was honest* — but nothing
proved the strategy was ever *tested against a real case*. A strategy could pass every gate and still be
wrong: a satellite strategy was approved four times while the pilot rejected it ("worse than the original").
The gates check governance, not truth. This adds the missing bar — the same way KEEL-104 makes approval the
human's recorded act, this makes the *reality outcome* a recorded, structural fact the gate requires to
exist (it never judges whether the outcome is "good"; the human does, at approval). Standalone governance
improvement, decided in ADR-0009 — hence `Strategy: none`.

## Plan
1. **Engine (`emkeel.process`)**: `new_state` stamps `steps_schema` (the process shape at creation) — the
   deterministic back-compat discriminator so each state is held to the bar of the schema that created it.
2. **Schema (`emkeel.strategy`)**: insert a `validated` step between `checked` and `presented`
   (`requires=(case, method, outcome, evidence_ref)`, `validate=_reality_validated`: `outcome` ∈
   `{pass,fail,mixed}`, `evidence_ref` resolved like an option Source); and add `kill_criteria` to
   `scaffolded.requires` (the abandon-conditions, declared up front).
3. **Gate (`check_strategy_process`)**: the merge bar moves to `validated` for reality-gated states; it
   re-validates the reality evidence (resolving a repo `evidence_ref` against the repo root) and enforces the
   **conscious override** — if `outcome` ∈ `{fail,mixed}` and the process reached `presented`, a recorded
   `proceed_justification` is required. Legacy states (no `steps_schema`/`validated`) keep the `checked` bar
   (grandfathered — never retroactively broken). The check is deterministic and never judges the outcome.
4. **Distributed `/strategy` skill prompt**: teach the `validated` step, `kill_criteria`, and
   `proceed_justification`, so an agent driving the engine records them (never hits a blind refusal).
5. **ADR-0009** recording the decision (reality, not just process). Version bump 0.1.96 → 0.1.97.

## Acceptance Criteria
1. The engine REFUSES `validated` without `case`/`method`/`outcome`/`evidence_ref`, on a bad `outcome` enum,
   or on a malformed-URL `evidence_ref`; a recorded `fail` outcome is accepted (an honest record).
2. `scaffolded` REFUSES without `kill_criteria`.
3. The gate FAILS a reality-gated strategy that stops at `checked` (reality bar not reached), on a bad
   `outcome` enum, and on a repo `evidence_ref` that does not resolve; it PASSES with a resolving repo ref or
   a well-formed URL.
4. **Conscious override**: outcome `fail`/`mixed` + reached `presented` without `proceed_justification` →
   FAIL; with a recorded `proceed_justification` → PASS. The gate never inspects the justification's content.
5. **Back-compat**: a legacy process state (no `steps_schema`, no `validated`) at `checked`/`presented`
   PASSES — touching an existing strategy doc does not retroactively break it.
6. The gate never judges whether the outcome is "good" (a recorded `pass` and `fail` both satisfy the
   structural check); approval remains the human merge (KEEL-104 invariant intact). Bump 0.1.97; all tests
   pass (engine + gate unit tests + the approval-integrity integration test).
