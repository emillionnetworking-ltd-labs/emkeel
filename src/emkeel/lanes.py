"""Single source of truth for the emkeel maintenance lane.

The lane is the branch convention (`emkeel-maint/<version>-<sha>`) that ships emkeel's OWN wiring
changes (`emkeel update` / `emkeel set`) through a scope-gated, **ticket-exempt** PR: `check_maint_scope`
proves it touches nothing but emkeel-managed files, so `check_ticket_link` (and the post-merge Jira
transition) skip the Jira-ticket requirement for it.

Every site that reasons about the lane imports `is_maint_lane` / `MAINT_PREFIX` from here — one
definition, no drifting hardcoded copies of the string. Zero dependencies, so anyone can import it.
"""

from __future__ import annotations

MAINT_PREFIX = "emkeel-maint/"


def is_maint_lane(branch: str | None) -> bool:
    """True if `branch` is an emkeel maintenance lane (`emkeel-maint/<version>-<sha>`)."""
    return (branch or "").startswith(MAINT_PREFIX)
