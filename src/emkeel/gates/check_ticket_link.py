"""Gate: the change must reference a ticket that EXISTS (e.g., KEEL-12).

Deterministic on the syntax (a ticket key in the branch/PR title) and — when the Jira secrets are
present — on EXISTENCE too: it GETs the issue and FAILS if Jira returns 404. This closes the gap where
a plausible-but-nonexistent key (a typo, or a ticket never created) sailed through. First link of
ticket->code traceability. "done" = this check passes, not a self-attested flag.

Degradation: secrets absent → existence is NOT verified (non-blocking ::warning::, syntax-only, as
before — keeps the gate usable offline / on forks without secrets). Secrets present + 404 → HARD FAIL.
A non-404 error (auth/5xx) is inconclusive → non-blocking ::warning:: (don't block a merge on a Jira
hiccup). The `emkeel-maint/*` lane stays exempt (no ticket required there).
"""

from __future__ import annotations

import os
import re
import sys

from emkeel.lanes import is_dependabot_lane, is_maint_lane

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


def _verify_exists(key: str, repo: str) -> int:
    """0 if the merge may proceed, 1 on a hard fail. Verifies the ticket EXISTS in Jira when secrets
    allow it; degrades to a non-blocking warning otherwise (see module docstring)."""
    from emkeel.jira import issue_status, secrets_present
    if not secrets_present():
        print(f"::warning::Ticket existence NOT verified for '{key}' — Jira secrets not set "
              f"(add JIRA_BASE_URL / JIRA_EMAIL / JIRA_TOKEN at "
              f"https://github.com/{repo}/settings/secrets/actions/new).")
        print(f"OK (syntax only): ticket '{key}' linked — existence unverified.")
        return 0
    status = issue_status(key)
    if status == 200:
        print(f"OK: ticket '{key}' exists in Jira.")
        return 0
    if status == 404:
        proj = key.split("-")[0]
        print(f"::error::Ticket '{key}' does not exist in Jira (HTTP 404). Create it first, e.g. "
              f"`emkeel jira create --project {proj} --summary \"...\"`, then re-run.", file=sys.stderr)
        print(f"FAIL: ticket '{key}' not found in Jira.", file=sys.stderr)
        return 1
    print(f"::warning::Could not verify '{key}' in Jira (HTTP {status}) — not blocking the merge.")
    print(f"OK (inconclusive): ticket '{key}' linked — existence check returned HTTP {status}.")
    return 0


def main() -> int:
    _warn_if_stale_wiring()
    branch = os.environ.get("EMKEEL_BRANCH", "")
    if is_maint_lane(branch):
        # Tool maintenance lane: no Jira ticket required — check_maint_scope guarantees the PR
        # touches only emkeel-managed files, so it can't smuggle code past traceability.
        print("OK: emkeel maintenance branch — no ticket required (scope-gated by check_maint_scope).")
        return 0
    if is_dependabot_lane(branch):
        # Dependabot lane: bot-created, no Jira ticket — check_dependabot_scope guarantees the PR
        # touches only dependency manifests/lockfiles + Actions bumps, so it can't smuggle code either.
        print("OK: dependabot branch — no ticket required (scope-gated by check_dependabot_scope).")
        return 0
    pr_title = os.environ.get("EMKEEL_PR_TITLE", "")
    key = find_ticket_key(branch, pr_title)
    _warn_if_project_mismatch(key)
    if not key:
        print(
            "FAIL: no ticket key found (e.g. KEEL-12) in the branch or PR title. "
            f"branch='{branch}' pr_title='{pr_title}'",
            file=sys.stderr,
        )
        return 1
    repo = os.environ.get("GITHUB_REPOSITORY", "OWNER/REPO")
    return _verify_exists(key, repo)


if __name__ == "__main__":
    sys.exit(main())
