# 12. Sprint placement is enforced at merge, not left to the agent relaying a notice

- Status: accepted
- Date: 2026-06-26
- Deciders: operator (EMillion Networking)
- Ticket: KEEL-117

## Context

KEEL-106/111 established the no-orphan invariant: when a project uses sprints, `emkeel jira create` always
produces a placement recommendation and leaves the ticket consciously in the backlog, labeled
`emkeel-placement-pending`, for the OPERATOR to decide the sprint. The recommendation is printed as a
`::notice::` on stderr, and the agent contract tells the agent to RELAY it to the operator.

That last link is prose, not a mechanism. If the agent doesn't relay the notice (or the window's CLI is
stale and the notice never fires), the operator is never asked and the ticket merges unplaced. This was
observed from the em-ecosystem window: ECO tickets — a sprint project — were not getting placed, because
nothing enforced the decision. It is the same failure mode as ticket-first (ADR-0011): a rule that depends on
an agent remembering it is a suggestion, not a gate.

## Decision

Enforce the placement decision at merge time, with the emkeel pattern of *gate + resolve command*:

- **The gate — `check_ticket_placed`**: for a ticket in a sprint-using project, FAIL iff it is still
  `emkeel-placement-pending` AND not in any sprint AND not Done. The signal is deterministic and
  label-independent where it matters: being in a sprint (the discovered Sprint custom-field is non-empty —
  placed via CLI or the Jira UI) is a decision and PASSES; a conscious move to the backlog (the pending label
  removed) is also a decision and PASSES. Only "never decided" (still flagged, not in a sprint) blocks the
  merge. Kanban projects have no sprints → N/A; `maint/*`/`dependabot/*` exempt; Jira unreachable / no
  secrets → inconclusive `::warning::` (never block on a hiccup), in parity with `check_ticket_link`.

- **The resolve command — `emkeel jira place <key> [--sprint active|backlog|<id>]`**: the operator decides
  from the console — it places the ticket (reusing `recommend_placement` / `_resolve_placement` /
  `place_issue`) and clears the pending label. So a blocked merge has a one-command fix that lives in the
  tool, not only in the Jira UI.

The Sprint custom-field id varies per Jira instance, so it is discovered via `/field` (by name), never
hardcoded — the gate is portable across instances.

## Consequences

- **The operator is reliably asked**: an unplaced sprint-project ticket cannot merge, so the placement
  decision surfaces at the gate regardless of whether the agent relayed the notice. Exported to every
  governed repo via `emkeel update`.
- **No weakening of KEEL-111**: the operator still decides (sprint or conscious backlog); emkeel still never
  auto-places into a sprint. What changed is that the decision is now non-skippable.
- **Honest scope**: the gate only acts on tickets emkeel flagged pending and on sprint projects — a Kanban
  project (e.g. emkeel's own KEEL board) is N/A, so this change does not block emkeel's own PRs.
- **Backstop + paved road**, the same shape as ticket-first: the gate enforces, `emkeel jira place` makes
  deciding easy.
