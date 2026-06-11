"""emkeel set — change a value in emkeel.toml cleanly (no hand-editing).

  emkeel set jira-project ECO
  emkeel set jira-url https://your.atlassian.net
  emkeel set github-repo owner/repo

Regenerates emkeel.toml from your existing values with the one field changed (the install
`source` pin and your governance artifacts are preserved). Commit the result.
"""

from __future__ import annotations

import sys
from pathlib import Path

from emkeel.init import _toml
from emkeel.update import load_cfg

FIELDS = {"jira-project": "jira_project", "jira-url": "jira_url", "github-repo": "github_repo"}


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    no_ship = "--no-ship" in argv
    argv = [a for a in argv if a != "--no-ship"]
    if len(argv) != 2 or argv[0] not in FIELDS:
        print(f"usage: emkeel set <{'|'.join(FIELDS)}> <value> [--no-ship]", file=sys.stderr)
        return 2
    field, value = argv
    target = Path(".")
    cfg = load_cfg(target)
    if cfg is None:
        print("  No emkeel.toml here — run `emkeel setup` first.", file=sys.stderr)
        return 1

    attr = FIELDS[field]
    old = getattr(cfg, attr)
    if old == value:
        print(f"{field} is already '{value}' — nothing to change.")
        return 0
    setattr(cfg, attr, value)
    (target / "emkeel.toml").write_text(_toml(cfg), encoding="utf-8")
    print(f"emkeel set — {field}: '{old}' → '{value}'  (emkeel.toml updated)")
    if not no_ship:
        from emkeel.ship import ship
        print("Shipping the change through the maintenance lane (PR → auto-merge)…")
        return ship(["emkeel.toml"], target)
    print("  --no-ship: commit emkeel.toml yourself, or run `emkeel update` to ship.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
