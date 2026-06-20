"""Single source of truth for the automated, ticket-exempt branch lanes.

A "lane" is a branch convention whose PRs are created by automation (not a person), so they carry no
Jira ticket — and `check_ticket_link` (plus the post-merge Jira transition) skip the ticket requirement
for them. Each lane stays honest via its own scope gate, so the exemption can NEVER smuggle real code:

- `emkeel-maint/<version>-<sha>` — emkeel's OWN wiring refresh (`emkeel update` / `emkeel set`);
  kept honest by `check_maint_scope` (only emkeel-managed files).
- `dependabot/<ecosystem>/...` — Dependabot dependency bumps; kept honest by `check_dependabot_scope`
  (only dependency manifests/lockfiles + GitHub Actions workflow bumps).

Every site that reasons about a lane imports its predicate / prefix from here — one definition, no
drifting hardcoded copies of the string. Zero dependencies, so anyone can import it.
"""

from __future__ import annotations

MAINT_PREFIX = "emkeel-maint/"
DEPENDABOT_PREFIX = "dependabot/"


def is_maint_lane(branch: str | None) -> bool:
    """True if `branch` is an emkeel maintenance lane (`emkeel-maint/<version>-<sha>`)."""
    return (branch or "").startswith(MAINT_PREFIX)


def is_dependabot_lane(branch: str | None) -> bool:
    """True if `branch` is a Dependabot lane (`dependabot/<ecosystem>/...`)."""
    return (branch or "").startswith(DEPENDABOT_PREFIX)
