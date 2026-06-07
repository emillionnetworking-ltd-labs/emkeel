"""Gate: the change must reference a ticket (e.g., KEEL-12).

Deterministic, runs in CI. Fails (exit 1) if no ticket key is found in the branch name
or the PR title. It is the first link of ticket->code traceability. "done" = this check
passes, not a self-attested flag.
"""

from __future__ import annotations

import os
import re
import sys

# Jira-style ticket key: 2+ uppercase letters, a hyphen, a number. e.g. KEEL-12, PROD-345.
KEY_RE = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b")


def find_ticket_key(*sources: str) -> str | None:
    """Return the first ticket key found across the given sources, or None."""
    for text in sources:
        match = KEY_RE.search(text or "")
        if match:
            return match.group(0)
    return None


def main() -> int:
    branch = os.environ.get("EMKEEL_BRANCH", "")
    pr_title = os.environ.get("EMKEEL_PR_TITLE", "")
    key = find_ticket_key(branch, pr_title)
    if key:
        print(f"OK: ticket '{key}' linked (branch='{branch}' pr_title='{pr_title}').")
        return 0
    print(
        "FAIL: no ticket key found (e.g. KEEL-12) in the branch or PR title. "
        f"branch='{branch}' pr_title='{pr_title}'",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
