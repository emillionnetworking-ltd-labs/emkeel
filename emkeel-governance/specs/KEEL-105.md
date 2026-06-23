# KEEL-105 — a ticket can't be born Done

Strategy: none (governance/process integrity — CLI guard, not a product feature)

## Context
Caught live: `emkeel jira create --status Done` created tickets **already terminal**, skipping
work→merge→Done. ECO-69 and ECO-70 were born `Done` ~1s after creation (ECO-70 was the BUILD, unstarted).
Verified it is the `--status` of `create`, not Jira automation (reopening the issue lands in `To Do`).
Invariant (the spirit of KEEL-104 applied to completion): **`Done` is EARNED by the work + the merge, never
auto-written at create.** Creation leaves the issue in the project's INITIAL state.

## Decision — remove `--status` from `create` entirely (vs. blocking only terminal statuses)
A terminal-status **denylist is fragile**: terminal names are localized and per-project (`Done`, `Closed`,
`Resolved`, `Resuelto`, `Cancelled`, `Won't Do`, …) — any one missed slips a born-terminal ticket through,
unacceptable for an integrity invariant. **Removing `--status` guarantees born-in-initial unconditionally**,
with no list to maintain, and matches the architecture: a status change goes through `emkeel jira
transition` + the merge, never creation. `--status` stays *parsed* only so a born-Done attempt gets a clear
red error (not argparse's opaque "unrecognized arguments"); it is rejected BEFORE creating, so nothing is
half-made.

## Plan
1. `_main_create`: reject any `--status` with a red `::error::` + exit 1 (before create); drop the
   post-create transition tail. A normal `create` makes the issue and never transitions it.
2. Docs/help: `create` makes the issue in the INITIAL state; no `--status`.
3. Agent contract (`_agents_md`): create in the initial state; `Done` is earned via `transition` + merge.

## Acceptance Criteria
1. `emkeel jira create --status Done` → red error + exit 1, and **nothing is created** (no POST).
2. A normal `create` → exit 0, issue created in the initial state, **never transitioned**.
3. The work→merge→Done path via `emkeel jira transition` is **intact** (still moves the issue to Done).
4. Integration test (per KEEL-103) reproducing the exact ECO-69/70 bug end-to-end. Bump 0.1.89; all tests
   pass.
