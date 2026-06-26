# 11. Ticket-first is enforced, not advised: a precedence gate + a paved-road command

- Status: accepted
- Date: 2026-06-26
- Deciders: operator (EMillion Networking)
- Ticket: KEEL-116

## Context

The lifecycle order is ticket → branch → code: the work is born from a ticket, and the branch/commits carry
its key. ADR-0004 added `check_ticket_link` to verify the ticket EXISTS at PR time — but existence is not
order. A ticket created *after* the implementation still passes: it's a post-hoc label, not the thing the
work was born from.

This is not hypothetical. KEEL-115 was implemented, committed, and verified — and only then was its ticket
created, last. The order was kept by discipline (and barely), not by a mechanism. That is exactly the
"best-effort prose that can be ignored" the agent contract warns about: if the order depends on an agent
remembering it, it is a suggestion, not a gate. The fix has to live in emkeel and be exported, so that
wherever emkeel governs, the correct order is enforced and a bypass is caught.

## Decision

Make ticket-first a mechanism, with two complementary pieces — the emkeel pattern of *paved road + backstop*:

- **The paved road — `emkeel start <summary> [--kind] [--project]`**: creates the Jira ticket first (the
  shared `create_and_place` core — same isolation/creds guards and sprint placement as `emkeel jira create`),
  reads the returned key, and `git checkout -b <kind>/<KEY>-<slug>`. Ticket-first **by construction**; the
  order cannot invert because the branch is named from a key that already exists. This is the primary fix —
  it makes the correct order the easy one and removes the temptation to create the ticket last.

- **The backstop — gate `check_ticket_precedes_work`**: a deterministic temporal fact. Jira's `created`
  timestamp (server-set, the agent can't backdate it) must be no later than the branch's earliest commit
  author-date (`git log --format=%aI`, author-date so it survives rebase), within a small clock-skew
  tolerance (3 min). Created after the work → FAIL. Exempt for `maint/*` and `dependabot/*`; Jira
  unreachable / no secrets / no comparable commit → inconclusive `::warning::` (never block a merge on a Jira
  hiccup), in parity with `check_ticket_link`. Wired into the generated CI, so every governed repo inherits
  it via `emkeel update`.

The gate's precision is bounded honestly: with squash workflows a branch may be a single commit, so it
really checks "ticket created before the commit (± skew)", and the skew window could let a just-after ticket
slip. That is acceptable because the *guarantee* is `emkeel start`; the gate catches the gross bypass (a
ticket created long after the work, or after the PR), which is the real failure mode KEEL-115 showed.

## Consequences

- **Ticket-first stops depending on discipline**: the command makes it automatic, the gate catches the
  manual bypass — exported to every repo that uses emkeel, not just kept in one agent's habits.
- **No weakening of existing rules**: `check_ticket_link` (existence) is untouched; `emkeel jira create` and
  `emkeel start` create through one shared core, so the no-born-Done rule and sprint placement are identical.
- **Honest limits**: the gate is a backstop with a skew window, documented as such; the load-bearing
  guarantee is the paved-road command. A future tightening (e.g. comparing against the branch point) can come
  if practice shows the window is abused.
- **Built ticket-first**: KEEL-116's own ticket existed before its branch, so the change passes its own gate
  — the rule is dogfooded from its first commit.
