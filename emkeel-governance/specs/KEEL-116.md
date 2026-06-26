# KEEL-116 — enforce ticket-first: check_ticket_precedes_work gate + emkeel start command

Strategy: none

## Context
The lifecycle order is ticket → branch → code, but nothing in emkeel enforced it. `check_ticket_link`
verifies the ticket EXISTS at PR time, not that it existed BEFORE the work — so a ticket created *after* the
implementation (a post-hoc label) sails through. This actually happened: KEEL-115 was implemented and
committed, then its ticket was created last. The order was kept by discipline, not by a mechanism — which is
exactly the "best-effort prose that can be ignored" the contract warns against. This makes ticket-first an
exported, deterministic part of emkeel, decided in ADR-0011 — hence `Strategy: none`.

## Plan
1. **`jira.issue_created(key)`**: reads Jira's server-set `created` timestamp (the agent can't backdate it).
2. **Gate `check_ticket_precedes_work`** (beside `check_ticket_link`): FAILS when `ticket.created` is later
   than the branch's first-commit author-date (`git log --format=%aI origin/<base>..HEAD | tail -1`) by more
   than a small clock-skew tolerance (3 min). Lanes `maint/*` and `dependabot/*` exempt; Jira down / no
   secrets → inconclusive `::warning::` (never blocks), in parity with `check_ticket_link`. Wired into the
   repo `ci.yml` and the generated `_ci_yaml` (every governed repo inherits it via `emkeel update`).
3. **Command `emkeel start <summary> [--kind feat|fix|chore|docs] [--project]`**: creates the ticket (the
   shared `create_and_place` core — same guards + sprint placement as `emkeel jira create`), reads the key,
   and `git checkout -b <kind>/<KEY>-<slug>` — ticket-first by construction (the paved road). The gate is the
   backstop for a manual flow that inverts the order.
4. **Agent contract** (`_agents_md`): ticket-first is no longer advice — point at `emkeel start` and the gate.
5. **ADR-0011**. Integration test (real git, ticket before/after the commit). Bump 0.1.99.

## Acceptance Criteria
1. The gate FAILS when the ticket was created after the first commit (beyond the 3-min skew), PASSES when it
   predates the commit, and PASSES within the skew tolerance.
2. Lanes `maint/*`/`dependabot/*` → N/A; no secrets / Jira error / no comparable commit → inconclusive (never
   blocks). A missing key is `check_ticket_link`'s FAIL, not this gate's.
3. `emkeel start <summary>` creates the ticket FIRST, then `git checkout -b <kind>/<KEY>-<slug>`; a failed
   ticket creation makes NO branch. `--kind` sets the prefix; the project defaults from `emkeel.toml`.
4. `emkeel jira create` and `emkeel start` create identically (shared `create_and_place`) — existing create
   behavior (guards, no born-Done, sprint placement) unchanged.
5. The gate is wired into the repo CI and the generated `_ci_yaml`. Real-git integration test covers
   before→PASS and after→FAIL. Bump 0.1.99; all tests pass. (This KEEL was itself built ticket-first — the
   ticket existed before the branch — so it passes its own gate.)
