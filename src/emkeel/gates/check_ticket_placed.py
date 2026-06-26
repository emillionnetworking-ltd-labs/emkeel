"""Gate: a ticket in a SPRINT-using project must have its placement DECIDED before merge.

emkeel surfaces a placement recommendation at create and leaves the ticket in the backlog labeled
`emkeel-placement-pending` (KEEL-106/111) — but whether the operator actually decides was left to the agent
relaying a notice. That's prose, not a mechanism: if the agent doesn't relay, the ticket merges unplaced.
This enforces it — the merge is blocked while the ticket is still undecided.

Deterministic signal: FAIL iff the ticket still carries the pending label AND is not in any sprint AND is not
Done. A conscious decision clears it — placed in a sprint (`emkeel jira place`, `--sprint`, or the Jira UI →
the Sprint field is non-empty) OR consciously moved to the backlog (the pending label removed). Kanban
projects have no sprints → N/A. Lanes `maint/*`/`dependabot/*` exempt; Jira down / no secrets → inconclusive
`::warning::` (never block on a hiccup), in parity with `check_ticket_link`.
"""

from __future__ import annotations

import os
import sys

from emkeel.gates.check_ticket_link import find_ticket_key
from emkeel.lanes import is_dependabot_lane, is_maint_lane


def _verify_placed(key: str) -> int:
    from emkeel.jira import _default_caller, _sprint_board, issue_placement_state, secrets_present
    if not secrets_present():
        print(f"::warning::Placement NOT verified for '{key}' — Jira secrets not set.")
        print(f"OK (unverified): '{key}' — placement check skipped (no secrets).")
        return 0
    project = key.split("-")[0]
    caller = _default_caller()
    board_id, reachable = _sprint_board(project, caller=caller)
    if not reachable:
        print(f"::warning::Could not reach the Jira Agile API for '{project}' — not blocking '{key}'.")
        print(f"OK (inconclusive): '{key}' — sprint usage undetermined.")
        return 0
    if board_id is None:
        print(f"OK: '{project}' is Kanban — no sprint placement applies (N/A).")
        return 0
    status, state = issue_placement_state(key, caller=caller)
    if status != 200 or state is None:
        print(f"::warning::Could not read '{key}' placement state (HTTP {status}) — not blocking.")
        print(f"OK (inconclusive): '{key}' — placement unverified (HTTP {status}).")
        return 0
    if state["done"]:
        print(f"OK: '{key}' is Done — placement moot (N/A).")
        return 0
    if state["pending_label"] and not state["in_sprint"]:
        print(f"::error::Ticket '{key}' is in a sprint-using project but its placement is still UNDECIDED "
              f"(labeled 'emkeel-placement-pending', not in any sprint). Decide it before merge: "
              f"`emkeel jira place {key} --sprint active|backlog|<id>` (or place it in Jira). "
              f"Merge is blocked until the placement decision is made.", file=sys.stderr)
        print(f"FAIL: '{key}' placement not decided.", file=sys.stderr)
        return 1
    print(f"OK: '{key}' placement decided (in a sprint or consciously placed).")
    return 0


def main() -> int:
    branch = os.environ.get("EMKEEL_BRANCH", "")
    if is_maint_lane(branch):
        print("OK: emkeel maintenance branch — no ticket required (placement N/A).")
        return 0
    if is_dependabot_lane(branch):
        print("OK: dependabot branch — no ticket required (placement N/A).")
        return 0
    pr_title = os.environ.get("EMKEEL_PR_TITLE", "")
    key = find_ticket_key(branch, pr_title)
    if not key:
        print("OK: no ticket key to check placement for (check_ticket_link owns the missing-key FAIL).")
        return 0
    return _verify_placed(key)


if __name__ == "__main__":
    sys.exit(main())
