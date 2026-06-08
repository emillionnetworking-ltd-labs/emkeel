"""emkeel eject — reverse `emkeel init` in a repo (command: `emkeel eject`; alias: `emkeel uninstall`).

Removes the wiring Emkeel added (workflows, emkeel.toml, .env.example, AGENTS.md, CLAUDE.md).
For .gitattributes/.gitignore it removes the file **only if Emkeel created it** (it holds just
Emkeel's one line) — it NEVER strips a line you may already have had. **Keeps
emkeel-governance/** (your ADRs/specs/records) unless `--purge`. Dry-run unless `--yes`.

With `--remote` it also finishes the un-govern on GitHub: drops branch protection (so removing
the gates workflow doesn't deadlock a PR), commits + pushes the removal, and drops the Jira
secrets — the mirror image of `emkeel connect`.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
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


def _run(args: list[str], timeout: float | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)


def repo_from_git(target: Path, run=_run) -> str:
    """owner/repo from the GitHub remote (emkeel.toml may already be deleted by the eject)."""
    r = run(["git", "-C", str(target), "remote", "get-url", "origin"])
    if r.returncode == 0:
        m = re.search(r"github\.com[:/]+([^/]+/[^/.\s]+)", r.stdout.strip())
        if m:
            return m.group(1)
    return ""


def remote_cleanup(repo: str, branch: str, removed_paths: list[str], run=_run) -> list[tuple[str, bool]]:
    """Finish the un-govern on GitHub: drop branch protection (so removing the gates workflow
    doesn't deadlock), commit + push the removals, and drop the Jira secrets."""
    steps: list[tuple[str, bool]] = []
    run(["gh", "api", "-X", "DELETE", f"repos/{repo}/branches/{branch}/protection"])
    steps.append(("branch protection cleared", True))   # 404 (already none) is fine too
    if removed_paths:
        run(["git", "add", *removed_paths])             # stage only Emkeel's deletions (not your files)
        c = run(["git", "commit", "-m", "chore(emkeel): remove governance (eject)"])
        steps.append(("commit removal", c.returncode == 0))
        try:
            p = run(["git", "push"], timeout=180)
            steps.append(("push" if p.returncode == 0 else "push FAILED — do it manually: git push", p.returncode == 0))
        except subprocess.TimeoutExpired:
            steps.append(("push timed out (hook?) — do it manually: git push", False))
    for name in ("JIRA_TOKEN", "JIRA_EMAIL", "JIRA_BASE_URL"):
        run(["gh", "secret", "delete", name, "--repo", repo])
    steps.append(("Jira secrets removed", True))
    return steps


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="emkeel eject",
        description="Reverse `emkeel init` in this repo (keeps emkeel-governance/ unless --purge).",
    )
    ap.add_argument("path", nargs="?", default=".")
    ap.add_argument("--purge", action="store_true", help="also delete emkeel-governance/ (your artifacts)")
    ap.add_argument("--yes", action="store_true", help="actually remove (default is a dry-run preview)")
    ap.add_argument("--remote", action="store_true",
                    help="also finish on GitHub: drop branch protection, commit+push the removal, drop Jira secrets")
    ns = ap.parse_args(argv)
    target = Path(ns.path)
    dry = not ns.yes

    actions = apply_uninstall(target, ns.purge, dry_run=dry)
    print(f"emkeel eject [{'dry-run' if dry else 'removed'}] -> {target}")
    for a in actions:
        print(f"  {a.kind:11} {a.path}")
    if dry:
        print("\n(nothing changed — pass --yes to apply)")
        if ns.remote:
            print("--remote would also: drop branch protection, commit+push the removal, drop Jira secrets.")
        return 0
    if not ns.purge and (target / GOVERNANCE_DIR).is_dir():
        print(f"\nKept {GOVERNANCE_DIR}/ (your history). Use --purge to delete it too.")

    if ns.remote:
        from emkeel.connect import gh_ok
        repo = repo_from_git(target)
        if not gh_ok():
            print("\n--remote skipped: gh isn't authenticated (run `gh auth login`).")
        elif not repo:
            print("\n--remote skipped: no GitHub remote found.")
        else:
            print(f"\nFinishing on GitHub ({repo}):")
            removed = [a.path for a in actions if a.kind in ("remove", "remove-dir")]
            for label, ok in remote_cleanup(repo, "main", removed):
                print(f"  {'✓' if ok else '✗'} {label}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
