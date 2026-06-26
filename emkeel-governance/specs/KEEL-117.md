# KEEL-117 — enforce sprint placement: check_ticket_placed gate + emkeel jira place

Strategy: none

## Context
KEEL-106/111 made `emkeel jira create` surface a placement recommendation and leave a sprint-project ticket
PENDING in the backlog (labeled `emkeel-placement-pending`), for the OPERATOR to decide. But whether the
decision actually happens was left to the AGENT relaying a stderr `::notice::` — prose, not a mechanism. If
the agent doesn't relay it, the ticket merges unplaced and the operator is never asked (observed from the
em-ecosystem window: ECO tickets not getting placed). Same lesson as KEEL-116 (ticket-first): if it matters,
enforce it in the tool. This blocks the merge until placement is decided. Standalone, decided in ADR-0012 —
hence `Strategy: none`.

## Plan
1. **`jira.issue_placement_state(key)`**: the deterministic facts — `pending_label` (still flagged
   undecided), `in_sprint` (the discovered Sprint custom-field is non-empty), `done` (status category).
   `jira.issue_created`-style; the Sprint field id is discovered via `/field`, never hardcoded.
2. **Gate `check_ticket_placed`**: FAIL iff the ticket is `pending_label AND not in_sprint AND not done`, on
   a sprint-using project. A sprint placement (CLI/UI → Sprint field set) OR a conscious backlog decision
   (pending label removed) PASSES. Kanban → N/A; maint/dependabot exempt; Jira down / no secrets →
   inconclusive (parity with `check_ticket_link`). Wired into `ci.yml` + `_ci_yaml`.
3. **`emkeel jira place <key> [--sprint active|backlog|<id>]`**: the operator's resolve path — places the
   ticket (reusing `recommend_placement`/`_resolve_placement`/`place_issue`) and clears the pending label.
4. **Agent contract**: the placement decision is not optional — relay it, and `emkeel jira place` / the gate.
5. **ADR-0012**. Integration test (real jira parsing via a stub caller). Bump 0.1.100.

## Acceptance Criteria
1. A sprint-project ticket that is pending + not in any sprint + not Done → gate FAIL (merge blocked).
2. The same ticket placed in a sprint (Sprint field non-empty, however placed) → PASS, even if the pending
   label lingers; a conscious backlog decision (pending label removed) → PASS; a Done ticket → N/A.
3. Kanban project → N/A; lanes maint/dependabot → N/A; no secrets / Agile unreachable / read error →
   inconclusive (never blocks).
4. `emkeel jira place <key> --sprint active|backlog|<id>` places the ticket AND clears the pending label;
   Kanban → no-op; a cross-project key is refused by the isolation guard.
5. The Sprint field id is discovered (not hardcoded). Real-jira-parsing integration test covers pending→FAIL,
   in-sprint→PASS, Kanban→N/A. Wired into the generated CI. Bump 0.1.100; all tests pass.
