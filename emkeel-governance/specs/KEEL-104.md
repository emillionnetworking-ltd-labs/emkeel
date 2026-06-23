# KEEL-104 — /strategy must not record a human approval that never happened

Strategy: none (governance/process integrity — engine + gate, not a product feature)

## Context
Incident (ECO-69): a committed `<topic>.process.json` read `"state":"approved"` with an
`approved_by:"operador"` while the operator was still at the gate, undecided. `approved_by` is a
**forgeable self-written field** with no backing, and `check_strategy_process` only required "up to
checked" — so the lying record would pass. The invariant: **the recorded `approved` can never precede the
real human approval.**

## Decision — mechanism (a), gate-only (justified)
The committed record **caps at `presented`**; **the approval IS the PR review + merge** (branch protection
requires a human approving review to merge). `approved` is granted by the merge — never self-stamped in the
file. Chosen over (b) "gate queries the PR's approving review":
- **Deterministic + offline** like every other gate — no `gh`-api/network, no review-timing race (CI runs
  before the review, so (b) would false-red until a re-run).
- The backing already exists and is **unforgeable by the agent**: the merge's required human review,
  recorded immutably in PR/git history. No extra field, no post-merge git machinery (which branch
  protection makes impractical anyway).

## Plan
1. **Backing** — `check_strategy_process` FAILS a committed `approved`: a file can't certify an approval the
   merge hasn't granted. The lane PR stops at `presented`; the merge is the approval. The distributed skill
   no longer runs `advance approved` in the PR.
2. **Reset on refinement** — `process.advance` resets the process when re-entering the FIRST step: a new
   refinement (new ticket, same `<topic>`) starts CLEAN; a prior refinement's `approved` never carries over.
   The engine never auto-advances `approved`.
3. **Harden the gate** — beyond "reached checked": reject a committed `approved`, and reject incoherent
   states (done steps must be a contiguous prefix of the schema with non-decreasing timestamps — no holes,
   no back-dating).

## Acceptance Criteria
1. A committed `<topic>.process.json` with a forged `approved` (no human backing) → gate FAILS.
2. A process at `presented` (the legitimate lane-PR terminal) → gate PASSES.
3. Re-entering the first step resets the process; a prior `approved` does not survive a refinement.
4. The gate rejects out-of-order/holey step sequences and back-dated timestamps.
5. Integration test (per KEEL-103) with the exact bug; the distributed skill + agent contract reflect the
   "merge is the approval" rule. Bump 0.1.88; all tests pass.
