# KEEL-85 — Centralize the `emkeel-maint/*` lane exemption (single source of truth) + fix the Jira-transition false-red

## Context
The rule "the `emkeel-maint/*` lane requires no Jira ticket" was duplicated and drifting:
`check_ticket_link` hardcoded `branch.startswith("emkeel-maint/")`, `check_maint_scope` hardcoded the same,
`ship.py` had its own `MAINT_PREFIX` — and `jira.py` (the post-merge transition) didn't know about the
lane at all. So every merge of `emkeel update` / `emkeel set` made `jira-transition.yml` look for a ticket,
find none, and exit 1 → a recurring **false red**.

## Plan
1. **Single source of truth**: new `src/emkeel/lanes.py` with the canonical `MAINT_PREFIX` and a pure
   `is_maint_lane(branch)` predicate. Zero dependencies, so every site can import it without cycles.
2. **Route all lane sites through it** (grep `emkeel-maint`): `check_ticket_link`, `check_maint_scope`,
   `ship.py` (re-exports `MAINT_PREFIX` from `lanes` for back-compat). None keeps its own copy of the
   string/logic. (The only remaining literal is `ship.py`'s tempfile dir prefix — not the lane predicate.)
3. **Fix `jira.py`**: in the transition `main()`, if the branch is a maint lane → print
   "OK: emkeel maintenance lane — no ticket to transition." and `return 0` (SKIP), mirroring the exemption
   `check_ticket_link` already applies. No more false red on the lane.

## Invariants
- Lib + thin CLI; the predicate is pure and importable. No behavior change for normal branches.
- The lane stays scope-gated (`check_maint_scope` unchanged in effect); the legitimate "normal branch with
  no ticket → fail" case is preserved.

## Acceptance Criteria
1. `is_maint_lane`: maint branch → True; normal branch / empty / None → False; `MAINT_PREFIX` canonical.
2. All lane sites (gates, ship, jira) reference the shared predicate/prefix — no hardcoded duplicates.
3. `jira` transition on an `emkeel-maint/*` branch → SKIP (exit 0), never reaching `transition_issue`
   (the bug).
4. `check_ticket_link` still exempts the maint lane (regression); a normal branch with no ticket still
   FAILS (legit case intact).

## Sequencing
Branched off main at 0.1.69; bumps to **0.1.71** (KEEL-84 / PR #86 holds 0.1.70). Merge after #86; the
version line may need a trivial rebase.
