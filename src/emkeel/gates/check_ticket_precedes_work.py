"""Gate: the ticket must PREDATE the work — created before the branch's first commit (ticket-first).

`check_ticket_link` proves the ticket EXISTS; this proves it existed BEFORE the work began. The lifecycle
order is ticket → branch → code; a ticket created AFTER the commits is a post-hoc label, not the thing the
work was born from. The signal is a deterministic temporal fact: Jira's `created` (server-set, the agent
can't backdate it) vs the author-date of the branch's EARLIEST commit (author-date survives rebase).

Backstop, not the whole guarantee: with squash workflows a branch may be a single commit, so this really
checks "ticket created before the commit (± a small clock-skew tolerance)". `emkeel start <summary>` makes
the order correct by construction; this gate catches a manual flow that inverts it. Lanes `maint/*` and
`dependabot/*` are exempt (no ticket). Jira unreachable / no secrets → inconclusive ::warning:: (never block
a merge on a Jira hiccup), in parity with `check_ticket_link`. Needs `fetch-depth: 0` for the base diff.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

from emkeel.gates.check_ticket_link import find_ticket_key
from emkeel.lanes import is_dependabot_lane, is_maint_lane

# Grace for clock skew between Jira's server and the committer's machine. Small on purpose: this is a
# backstop (the real guarantee is `emkeel start`), so the window where a just-after ticket slips through
# is kept narrow rather than judging intent.
SKEW_TOLERANCE = timedelta(minutes=3)


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True)


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.strip().replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def first_commit_date(base: str, run=_run) -> datetime | None:
    """Author-date of the branch's EARLIEST commit over `origin/<base>..HEAD` (None if unknown). Author-date
    (not committer-date) survives rebase, so it tracks when the work was actually authored."""
    r = run(["git", "log", "--format=%aI", f"origin/{base}..HEAD"])
    lines = [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]
    return _parse_iso(lines[-1]) if lines else None     # last line = earliest commit


def _verify_precedes(key: str, base: str) -> int:
    from emkeel.jira import issue_created, secrets_present
    if not secrets_present():
        print(f"::warning::Ticket precedence NOT verified for '{key}' — Jira secrets not set.")
        print(f"OK (unverified): '{key}' — precedence check skipped (no secrets).")
        return 0
    status, created_raw = issue_created(key)
    created = _parse_iso(created_raw)
    if status != 200 or created is None:
        print(f"::warning::Could not read '{key}' created time in Jira (HTTP {status}) — not blocking.")
        print(f"OK (inconclusive): '{key}' — precedence unverified (HTTP {status}).")
        return 0
    first = first_commit_date(base)
    if first is None:
        print(f"::warning::Could not read the branch's first commit date — not blocking '{key}'.")
        print(f"OK (inconclusive): '{key}' — no comparable commit date.")
        return 0
    if created <= first + SKEW_TOLERANCE:
        print(f"OK: ticket '{key}' (created {created.isoformat()}) predates the work "
              f"(first commit {first.isoformat()}).")
        return 0
    print(f"::error::Ticket '{key}' was created AFTER the work began — created {created.isoformat()}, but the "
          f"branch's first commit is {first.isoformat()}. In this lifecycle the ticket comes FIRST: create it "
          f"(or use `emkeel start <summary>`), then branch + commit.", file=sys.stderr)
    print(f"FAIL: ticket '{key}' was created after the first commit.", file=sys.stderr)
    return 1


def main() -> int:
    branch = os.environ.get("EMKEEL_BRANCH", "")
    if is_maint_lane(branch):
        print("OK: emkeel maintenance branch — no ticket required (precedence N/A).")
        return 0
    if is_dependabot_lane(branch):
        print("OK: dependabot branch — no ticket required (precedence N/A).")
        return 0
    base = os.environ.get("EMKEEL_BASE_REF") or "main"
    pr_title = os.environ.get("EMKEEL_PR_TITLE", "")
    key = find_ticket_key(branch, pr_title)
    if not key:
        # A missing key is `check_ticket_link`'s FAIL to own — not this gate's concern.
        print("OK: no ticket key to check precedence for (check_ticket_link owns the missing-key FAIL).")
        return 0
    return _verify_precedes(key, base)


if __name__ == "__main__":
    sys.exit(main())
