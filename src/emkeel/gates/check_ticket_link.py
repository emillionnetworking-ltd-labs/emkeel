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


def _warn_if_stale_wiring() -> None:
    """Non-blocking nudge on every PR: if the repo's generated files drift from the current
    templates, tell the user to run `emkeel update`. Lives in a gate the CI already runs via
    `pip install emkeel`, so it reaches every repo without the workflow YAML needing to change."""
    try:
        from pathlib import Path
        from emkeel.update import wiring_drift
        drift = wiring_drift(Path("."))
        if drift:
            print(f"::warning::Emkeel wiring is out of date ({', '.join(drift)}). "
                  "Run `emkeel update` locally and commit to refresh it.")
    except Exception:
        pass  # a nudge must never break the gate


def _warn_if_project_mismatch(key: str) -> None:
    """Non-blocking nudge: if the ticket key's project (ECO in ECO-1) differs from the project
    declared in emkeel.toml (e.g. SCRUM), the config and the actual work have drifted apart."""
    try:
        from pathlib import Path
        from emkeel.update import load_cfg
        cfg = load_cfg(Path("."))
        declared = cfg.jira_project if cfg else ""
        used = key.split("-")[0] if key else ""
        if declared and used and used != declared:
            print(f"::warning::Branch uses '{key}' but emkeel.toml declares project '{declared}'. "
                  f"Align them — update emkeel.toml (or use {declared}-* keys).")
    except Exception:
        pass  # a nudge must never break the gate


def main() -> int:
    _warn_if_stale_wiring()
    branch = os.environ.get("EMKEEL_BRANCH", "")
    if branch.startswith("emkeel-maint/"):
        # Tool maintenance lane: no Jira ticket required — check_maint_scope guarantees the PR
        # touches only emkeel-managed files, so it can't smuggle code past traceability.
        print("OK: emkeel maintenance branch — no ticket required (scope-gated by check_maint_scope).")
        return 0
    pr_title = os.environ.get("EMKEEL_PR_TITLE", "")
    key = find_ticket_key(branch, pr_title)
    _warn_if_project_mismatch(key)
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
