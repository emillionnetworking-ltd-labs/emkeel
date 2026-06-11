"""Ship emkeel-managed changes through governance: branch → commit → push → PR → auto-merge.

Used by `emkeel update --ship <KEY>` / `emkeel set ... --ship <KEY>` so a wiring refresh doesn't sit
uncommitted — but still goes through a PR + the gates (NEVER a direct push to main). Reuses
connect.py's machinery: the push inherits the terminal (a pre-push hook stays visible), the PR is
created via gh, and GitHub's native auto-merge lands it WHEN the required checks pass.

Run it from your default branch: it forks `chore/<KEY>-emkeel-update`, commits only the
emkeel-managed files you pass, and opens the PR from there.
"""

from __future__ import annotations

import re
from pathlib import Path

from emkeel import connect

KEY_RE = re.compile(r"^[A-Z][A-Z0-9]+-\d+$")


def ship_key_from(argv) -> str | None:
    """The value after `--ship` in argv (empty string if the flag has no value), or None if absent."""
    argv = argv or []
    if "--ship" in argv:
        i = argv.index("--ship")
        return argv[i + 1] if i + 1 < len(argv) else ""
    return None


def ship(key: str, paths: list[str], target: Path = Path("."), run=connect._run) -> int:
    if not KEY_RE.match(key or ""):
        print(f"  --ship needs a ticket key like KEEL-12 (got '{key}').")
        return 2

    paths = [p for p in paths if (target / p).exists()]
    if not paths:
        print("  Nothing to ship (no changed files).")
        return 0

    if not connect.gh_ok(run):
        print("  gh is not authenticated — run `gh auth login`, then commit/push yourself.")
        return 1
    cfg = connect.load_config(target)
    repo = cfg.repo if cfg else ""

    branch = f"chore/{key}-emkeel-update"
    if run(["git", "-C", str(target), "checkout", "-b", branch]).returncode != 0:
        run(["git", "-C", str(target), "checkout", branch])   # branch exists → reuse it
    run(["git", "-C", str(target), "add", *paths])
    commit = run(["git", "-C", str(target), "commit", "-m", f"chore: refresh emkeel wiring ({key})"])
    blob = ((commit.stdout or "") + (commit.stderr or "")).lower()
    if commit.returncode != 0 and "nothing to commit" not in blob:
        print(f"  commit failed: {(commit.stderr or commit.stdout).strip()}")
        return 1

    print("  Pushing… (a pre-push hook may run — Ctrl-C to skip)")
    ok, msg = connect.do_push(run)
    if not ok:
        print(f"  push failed: {msg}")
        return 1
    ok, msg = connect.do_pr_create(run)
    if not ok:
        print(f"  PR create: {msg}")
        return 1
    print(f"  PR opened: {msg}")
    if repo:
        connect.allow_auto_merge(repo, run)
    ok, msg = connect.do_auto_merge(run)
    print("  ✓ auto-merge enabled — it lands when the gates pass." if ok else f"  auto-merge: {msg}")
    return 0
