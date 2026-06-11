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
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 2 or argv[0] not in FIELDS:
        print(f"usage: emkeel set <{'|'.join(FIELDS)}> <value>", file=sys.stderr)
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
    print(f"emkeel set — {field}: '{old}' → '{value}'  (emkeel.toml updated; commit it)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
