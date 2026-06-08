"""emkeel command-line interface.

Subcommands:
  emkeel setup           interactive setup wizard (no AI — asks a few questions, does the work)
  emkeel init [opts]     scaffold a repo for Emkeel governance (non-interactive, for scripts/AI)
  emkeel onboard         print the AI-assisted onboarding playbook (paste it to your agent)
  emkeel review <KEY>    print a per-criterion review template for a ticket
  emkeel eject           reverse `emkeel init` in this repo (alias: uninstall; dry-run unless --yes)
  emkeel doctor          check what's set up and what's still pending (with fix links)
  emkeel connect         automate the GitHub side via gh (branch protection, secrets; new repo: create+push)
  emkeel version         show the installed version (and if a newer one is on PyPI)
"""

from __future__ import annotations

import sys
from importlib import resources

_USAGE = "usage: emkeel <setup|init|onboard|review|eject|doctor|connect|version> [args]   (try: emkeel setup)"


def _onboard() -> int:
    text = resources.files("emkeel").joinpath("_docs/onboarding.md").read_text(encoding="utf-8")
    print("# ── Paste everything below to your AI coding agent (Claude Code, Cursor, Copilot, ...).")
    print("# It will ask you for your GitHub repo, Jira URL and project key, then set Emkeel")
    print("# up step by step — in your language. (Or just follow it yourself.)")
    print("# " + "─" * 76)
    print()
    print(text)
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        print(_USAGE)
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "setup":
        from emkeel.wizard import main as wizard_main
        return wizard_main(rest)
    if cmd == "doctor":
        from emkeel.doctor import main as doctor_main
        return doctor_main(rest)
    if cmd == "connect":
        from emkeel.connect import main as connect_main
        return connect_main(rest)
    if cmd in ("version", "--version", "-V"):
        from emkeel.version import main as version_main
        return version_main(rest)
    if cmd == "init":
        from emkeel.init import main as init_main
        return init_main(rest)
    if cmd == "review":
        from emkeel.review import main as review_main
        return review_main(rest)
    if cmd == "onboard":
        return _onboard()
    if cmd in ("eject", "uninstall"):  # uninstall = backward-compat alias
        from emkeel.uninstall import main as eject_main
        return eject_main(rest)
    print(f"unknown command: {cmd}\n{_USAGE}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
