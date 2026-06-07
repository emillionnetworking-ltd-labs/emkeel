"""emkeel uninstall — reverse `emkeel init` in a repo.

Removes the wiring Emkeel added (workflows, emkeel.toml, .env.example, AGENTS.md, CLAUDE.md).
For .gitattributes/.gitignore it removes the file **only if Emkeel created it** (it holds just
Emkeel's one line) — it NEVER strips a line you may already have had. **Keeps
emkeel-governance/** (your ADRs/specs/records) unless `--purge`. Dry-run unless `--yes`.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from emkeel.init import APPEND_LINES

# Pure-wiring files that `emkeel init` creates (safe to remove on uninstall).
WIRING_FILES = [
    ".github/workflows/emkeel-ci.yml",
    ".github/workflows/jira-transition.yml",
    "emkeel.toml",
    ".env.example",
    "AGENTS.md",
    "CLAUDE.md",
]
GOVERNANCE_DIR = "emkeel-governance"


@dataclass
class Action:
    path: str
    kind: str  # "remove" | "remove-dir" | "keep" | "leave" | "absent"


def plan_uninstall(target: Path, purge: bool) -> list[Action]:
    actions: list[Action] = []
    for rel in WIRING_FILES:
        actions.append(Action(rel, "remove" if (target / rel).is_file() else "absent"))
    for rel, line in APPEND_LINES.items():
        p = target / rel
        if not p.is_file():
            actions.append(Action(rel, "absent"))
            continue
        nonblank = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
        # Remove the file only if Emkeel created it (it holds just our one line);
        # otherwise leave it untouched — never strip a line the user may already have.
        actions.append(Action(rel, "remove" if nonblank == [line] else "leave"))
    gov = target / GOVERNANCE_DIR
    if gov.is_dir():
        actions.append(Action(GOVERNANCE_DIR, "remove-dir" if purge else "keep"))
    return actions


def apply_uninstall(target: Path, purge: bool, dry_run: bool) -> list[Action]:
    actions = plan_uninstall(target, purge)
    if dry_run:
        return actions
    for a in actions:
        p = target / a.path
        if a.kind == "remove":
            p.unlink(missing_ok=True)
        elif a.kind == "remove-dir":
            shutil.rmtree(p, ignore_errors=True)
        # "leave" / "keep" / "absent" → do nothing
    return actions


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="emkeel uninstall",
        description="Reverse `emkeel init` (keeps emkeel-governance/ unless --purge).",
    )
    ap.add_argument("path", nargs="?", default=".")
    ap.add_argument("--purge", action="store_true", help="also delete emkeel-governance/ (your artifacts)")
    ap.add_argument("--yes", action="store_true", help="actually remove (default is a dry-run preview)")
    ns = ap.parse_args(argv)
    target = Path(ns.path)
    dry = not ns.yes

    actions = apply_uninstall(target, ns.purge, dry_run=dry)
    print(f"emkeel uninstall [{'dry-run' if dry else 'removed'}] -> {target}")
    for a in actions:
        print(f"  {a.kind:11} {a.path}")
    if dry:
        print("\n(nothing changed — pass --yes to apply)")
    elif not ns.purge and (target / GOVERNANCE_DIR).is_dir():
        print(f"\nKept {GOVERNANCE_DIR}/ (your history). Use --purge to delete it too.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
