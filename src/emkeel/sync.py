"""emkeel sync — bring your local back in shape after the adopt PR merges.

Switches to the default branch, pulls, prunes, and deletes local branches that are already
merged (detected via `--merged` OR an upstream that's `gone` — which catches squash-merges,
where the branch commits aren't ancestors of the default). Safe + idempotent.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path


def _run(args: list[str], capture: bool = True, timeout: float | None = None) -> subprocess.CompletedProcess:
    if capture:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    return subprocess.run(args, text=True, timeout=timeout)   # inherit the terminal (auth prompts)


def default_branch(run=_run) -> str:
    r = run(["git", "symbolic-ref", "refs/remotes/origin/HEAD"])
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip().rsplit("/", 1)[-1]
    return "main"


def _own(name: str) -> bool:
    return name.split("/", 1)[0] in ("chore", "feat", "fix")


def cleanable_branches(default: str, run=_run) -> list[str]:
    """Local chore/feat/fix branches safe to delete: merged into default, or upstream gone."""
    found: set[str] = set()
    merged = run(["git", "branch", "--merged", default])
    if merged.returncode == 0:
        for ln in merged.stdout.splitlines():
            n = ln.replace("*", "").strip()
            if n and n != default and _own(n):
                found.add(n)
    vv = run(["git", "branch", "-vv"])
    if vv.returncode == 0:
        for ln in vv.stdout.splitlines():
            if ": gone]" in ln:
                n = ln.replace("*", "").strip().split(" ", 1)[0]
                if _own(n):
                    found.add(n)
    return sorted(found)


def sync(run=_run) -> list[str]:
    out: list[str] = []
    db = default_branch(run)
    run(["git", "checkout", db], capture=False)
    out.append(f"✓ on {db}")
    p = run(["git", "pull", "--ff-only"], capture=False)
    out.append("✓ pulled" if p.returncode == 0 else "⚠ pull skipped (do it manually: git pull)")
    run(["git", "fetch", "--prune"])
    gone = cleanable_branches(db, run)
    for b in gone:
        run(["git", "branch", "-D", b])
    out.append(f"✓ removed merged branch(es): {', '.join(gone)}" if gone else "✓ no merged branches to clean")
    return out


def wait_for_merge(pr_ref: str, run=_run, tries: int = 20, delay: float = 15.0, sleep=time.sleep) -> bool:
    """Poll until the PR on `pr_ref` (branch or number) is MERGED. Returns False on timeout."""
    for i in range(tries):
        r = run(["gh", "pr", "view", pr_ref, "--json", "state", "-q", ".state"])
        if r.returncode == 0 and r.stdout.strip() == "MERGED":
            return True
        if i < tries - 1:
            sleep(delay)
    return False


def main(argv: list[str] | None = None) -> int:
    print("\n  emkeel sync")
    for line in sync():
        print("  " + line)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
