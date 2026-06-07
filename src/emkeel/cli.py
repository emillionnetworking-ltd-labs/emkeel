"""emkeel command-line interface.

Subcommands:
  emkeel init [opts]     scaffold a repo for Emkeel governance
  emkeel onboard         print the AI-assisted onboarding playbook (paste it to your agent)
  emkeel review <KEY>    print a per-criterion review template for a ticket
"""

from __future__ import annotations

import sys
from importlib import resources

_USAGE = "usage: emkeel <init|onboard|review> [args]   (try: emkeel onboard)"


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
    if cmd == "init":
        from emkeel.init import main as init_main
        return init_main(rest)
    if cmd == "review":
        from emkeel.review import main as review_main
        return review_main(rest)
    if cmd == "onboard":
        return _onboard()
    print(f"unknown command: {cmd}\n{_USAGE}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
