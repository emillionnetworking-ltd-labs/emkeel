# KEEL-106 — no ticket is orphaned in silence (sprint placement)

Strategy: none (governance/process integrity — CLI behavior, not a product feature)

## Context
Incident: **53 ECO tickets ended up with no sprint** because nothing guided their placement. Invariant
(the spirit of KEEL-104/105 applied to organization): when the project uses sprints, emkeel **ALWAYS**
surfaces a placement recommendation and **ALWAYS** applies a placement — active sprint, a future sprint via
the backlog — never "no recommendation / no decision". The *result* is flexible; the **no-silence is
inviolable**. It must hold on the non-interactive **agent** path too ("create the ticket first").

## Design — `emkeel jira create`, after the issue is created
Conditional on the project actually using sprints (it has a **scrum board**; Kanban → N/A):
1. **Always recommend** (`recommend_placement`): the **active sprint** if one is running (the work has a
   home), else the **backlog**. Always a concrete `Placement` with a rationale — never "none of the above".
2. **Always place** (`place_issue`): default = the recommendation (so the agent path needs no flag);
   `--sprint active|backlog|<id>` overrides. `active_sprint` → add to the sprint; `backlog` → an explicit
   move (a conscious decision, not a silent no-op).
3. **Always surfaced**: the recommendation prints as a `::notice::` and the applied placement is echoed —
   on **stderr**, so stdout stays just the key (scriptable). The agent flow is unbroken (create still
   returns the key, exit 0).
4. **Best-effort + non-fatal, never silent**: the ticket already exists, so an Agile-API hiccup or an
   `indeterminate` detection is a loud `::warning::` ("place it manually so it isn't orphaned"), never a
   create failure and never a silent orphan.

Detection is via the Jira Agile API (`/rest/agile/1.0/board?type=scrum`), the caller injected for tests.

## Acceptance Criteria
1. Project uses sprints + an active sprint running, agent `create` (no flag) → recommendation surfaced AND
   the ticket added to the active sprint.
2. Uses sprints, no active sprint → recommendation surfaced AND the ticket consciously placed in the backlog.
3. Kanban (no scrum board) → N/A: no sprint noise, create unaffected.
4. `--sprint backlog` overrides an active-sprint recommendation (chosen placement wins; the recommendation
   is still surfaced).
5. stdout stays just the key; the agent flow isn't broken. Integration test (per KEEL-103) reproducing the
   orphan incident. Bump 0.1.90; all tests pass.
