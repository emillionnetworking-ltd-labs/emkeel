"""emkeel command-line interface.

Subcommands:
  emkeel setup           interactive setup wizard — asks a few questions, does the work
  emkeel init [opts]     scaffold a repo for Emkeel governance (non-interactive, for scripts)
  emkeel review <KEY>    print a per-criterion review template for a ticket
  emkeel eject           reverse `emkeel init` in this repo (alias: uninstall; interactive)
  emkeel doctor          check what's set up and what's still pending (with fix links)
  emkeel connect         automate the GitHub side via gh (branch protection, secrets; new repo: create+push)
  emkeel sync            after the adopt PR merges: checkout default + pull + delete the merged branch
  emkeel update          refresh the wiring AND ship it (maintenance lane → PR → auto-merge); --no-ship to leave pending
  emkeel set <f> <v>     change an emkeel.toml value (jira-project | jira-url | github-repo) and ship it; --no-ship too
  emkeel strategy …      scaffold (new <topic>) + lint (check) researched strategy artifacts
  emkeel jira create …   create a Jira issue in the project's INITIAL state (--project --summary [--type Task]); Done is earned via transition + merge, not at create
  emkeel version         show the installed version (and if a newer one is on PyPI)
"""

from __future__ import annotations

import os
import sys

_USAGE = "usage: emkeel <setup|init|review|eject|doctor|connect|sync|update|set|strategy|jira|guard|version> [args]   (try: emkeel setup)"

# Commands that already speak to wiring/cred state (don't double-nudge) or run hot (guard = every tool call).
_NO_NUDGE = {"doctor", "update", "connect", "guard", "version", "--version", "-V", "-h", "--help"}


def _maybe_nudge(cmd: str) -> None:
    """Proactive, cheap, FAIL-SAFE 'git-hint' to stderr: if the repo wiring is behind the CLI or the
    scoped credential is missing, point at `emkeel update` / `emkeel connect`. Never blocks/raises; no
    network; honored off via EMKEEL_NO_UPDATE_CHECK; silent for the commands that already report state."""
    if cmd in _NO_NUDGE or os.environ.get("EMKEEL_NO_UPDATE_CHECK"):
        return
    try:
        from emkeel.doctor import wiring_nudge
        msg = wiring_nudge()
        if msg:
            print(msg, file=sys.stderr)
    except Exception:
        pass


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        print(_USAGE)
        return 0
    cmd, rest = argv[0], argv[1:]
    _maybe_nudge(cmd)
    if cmd == "setup":
        from emkeel.wizard import main as wizard_main
        return wizard_main(rest)
    if cmd == "doctor":
        from emkeel.doctor import main as doctor_main
        return doctor_main(rest)
    if cmd == "connect":
        from emkeel.connect import main as connect_main
        return connect_main(rest)
    if cmd == "sync":
        from emkeel.sync import main as sync_main
        return sync_main(rest)
    if cmd == "update":
        from emkeel.update import main as update_main
        return update_main(rest)
    if cmd == "set":
        from emkeel.setcfg import main as set_main
        return set_main(rest)
    if cmd == "strategy":
        from emkeel.strategy import main as strategy_main
        return strategy_main(rest)
    if cmd == "jira":
        from emkeel.jira import main as jira_main
        return jira_main(rest)
    if cmd == "guard":
        from emkeel.isolation import main as guard_main
        return guard_main(rest)
    if cmd in ("version", "--version", "-V"):
        from emkeel.version import main as version_main
        return version_main(rest)
    if cmd == "init":
        from emkeel.init import main as init_main
        return init_main(rest)
    if cmd == "review":
        from emkeel.review import main as review_main
        return review_main(rest)
    if cmd in ("eject", "uninstall"):  # uninstall = backward-compat alias
        from emkeel.uninstall import main as eject_main
        return eject_main(rest)
    print(f"unknown command: {cmd}\n{_USAGE}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
