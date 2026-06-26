"""emkeel start <summary> — TICKET FIRST, then a branch named from the new key.

The lifecycle order is ticket → branch → code. This command makes that order the EASY path (correct by
construction): it creates the Jira ticket with the same guards + sprint placement as `emkeel jira create`,
reads the returned KEY, and `git checkout -b <kind>/<KEY>-<slug>`. The `check_ticket_precedes_work` gate is
the backstop that catches a manual flow which inverts the order.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from emkeel.strategy import slug

_KINDS = ("feat", "fix", "chore", "docs")


def _derive_project(explicit: str | None) -> str | None:
    if explicit:
        return explicit
    try:
        from emkeel.update import load_cfg
        cfg = load_cfg(Path("."))
        return cfg.jira_project if cfg else None
    except Exception:
        return None


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    ap = argparse.ArgumentParser(
        prog="emkeel start",
        description="Create a Jira ticket FIRST, then a branch named from its key (the correct lifecycle order).")
    ap.add_argument("summary", nargs="+", help="the ticket summary (also slugified into the branch name)")
    ap.add_argument("--kind", default="feat", choices=_KINDS, help="branch prefix (default: feat)")
    ap.add_argument("--project", default=None, help="Jira project key (default: from emkeel.toml)")
    ap.add_argument("--type", dest="issuetype", default="Task")
    ns = ap.parse_args(argv)

    summary = " ".join(ns.summary).strip()
    project = _derive_project(ns.project)
    if not project:
        print("::error::no Jira project — pass --project KEY (none declared in emkeel.toml).", file=sys.stderr)
        return 1

    from emkeel.jira import create_and_place
    code, key = create_and_place(project, summary, ns.issuetype)   # same guards + placement as `jira create`
    if code != 0 or not key:
        return code or 1                                           # create_and_place already errored RED

    branch = f"{ns.kind}/{key}-{slug(summary)}"
    r = subprocess.run(["git", "checkout", "-b", branch], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"::error::ticket {key} created, but `git checkout -b {branch}` failed: {r.stderr.strip()}\n"
              f"Create the branch yourself: git checkout -b {branch}", file=sys.stderr)
        return 1
    print(f"✓ {key} created → branch {branch}  (ticket first, then the work)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
