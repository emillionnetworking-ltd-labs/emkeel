# 9. The /strategy reality gate: validate against a real case, not just a complete process

- Status: accepted
- Date: 2026-06-26
- Deciders: operator (EMillion Networking)
- Ticket: KEEL-114

## Context

ADR-0005 made `/strategy` a non-skippable governed-process state machine: every step records the evidence it
happened, and CI refuses an out-of-order or evidence-less advance. That closed *process* dishonesty — a step
can't be silently skipped. It did **not** close *result* dishonesty: every step (researched, proposed,
critiqued, checked, presented, approved) proves the process ran, but **none proves the strategy was tested
against a real case**. A strategy can pass every gate and still be wrong.

This is not hypothetical. A satellite strategy was approved four times (ECO-62 → 64 → 69 → 71) while the
pilot rejected it each time ("worse than the original", "espantoso"). The gate said APPROVED while reality
said FAILED, and nothing caught it — the gates validate governance, not truth.

A gate cannot judge whether a strategy "works" (that is human and subjective). But — exactly as KEEL-104
does not judge an approval and only requires that a human *recorded* it (approval = the merge) — a gate
**can** require that the *evidence of a reality test exists and is well-formed*, forcing the human to run the
test and record the outcome before approval. The gate checks presence/structure deterministically; the human
judges the result.

## Decision

Add a **reality gate** to the `/strategy` process — "realidad, no solo proceso":

- **A new `validated` step**, between `checked` and `presented` (so it sits below the KEEL-104 committed cap
  of `presented` and is therefore committable + checkable). It records structured evidence that the
  recommendation was applied to ONE real case: `case`, `method`, `outcome` ∈ a closed enum
  `{pass, fail, mixed}`, and an `evidence_ref` resolved the same way option Sources are (a repo `file:line`
  must resolve, a URL must be well-formed, an external citation is surfaced for the human). A recorded `fail`
  is a valid, honest record — **the gate never judges whether the outcome is "good"**, only that it exists
  and is structurally sound.
- **Kill-criteria declared up front**: `scaffolded` now requires `kill_criteria` — the conditions under
  which the strategy should be abandoned, named before the work, not rationalized after.
- **A conscious override**: if the recorded `outcome` is `fail`/`mixed` and the process proceeds to
  `presented` toward approval, a recorded `proceed_justification` is required. Approving despite a failed
  reality test becomes a deliberate, on-record act — never silent. The gate checks presence, never content.
- **Back-compat by schema stamp**: `new_state` records `steps_schema` (the process shape at creation). The
  gate holds each state to the bar of the schema that created it; states predating this change (no
  `validated`) keep the `checked` bar and are **grandfathered** — never retroactively broken.

The mechanism is the same pattern as KEEL-104, applied to results: the gate forces the evidence to EXIST and
be structurally valid; the human judges it at the merge. Deterministic, content-blind, non-skippable.

## Consequences

- **The demonstrated hole is closed**: a strategy can no longer reach approval without a recorded reality
  outcome; a `fail` is visible in the committed `<topic>.process.json` at the PR, so "approved while reality
  failed" becomes structurally impossible to do silently.
- **Cheap and real**: the reality test is "apply the recommendation to one real case and record what
  happened" — a pointer to resolvable proof, not a heavyweight pilot artifact.
- **No escape hatch** (deliberate): there is no "reality not applicable" flag — that valve is exactly the
  hole that reintroduces the disease. Start strict and reversible; add a justified valve only if reality ever
  demands it.
- **KEEL-104 intact**: `validated` is below the `presented` cap, so the committed file still cannot
  self-certify `approved`; approval remains the human merge.
- **Deferred (not in this ADR)**: a `history[]` accumulator + a refinement-loop detector that forces an
  explicit kill-or-pivot after N reality-fails. It touches the engine's clean-restart re-entry (the KEEL-104
  invariant) and only catches same-topic loops, so it waits until this reality gate proves out in practice.
