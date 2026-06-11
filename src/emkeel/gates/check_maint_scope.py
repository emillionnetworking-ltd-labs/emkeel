"""Gate: the emkeel maintenance lane may touch ONLY emkeel-managed files.

Deterministic, runs in CI. This is what makes the no-ticket `emkeel-maint/*` lane honest: a
maintenance PR that changes anything beyond the files Emkeel generates FAILS — so the lane can't be
used to merge real code without a ticket. For any other branch it's a no-op (N/A).

Needs the workflow to check out full history (`fetch-depth: 0`) so it can diff against the base.
"""

from __future__ import annotations

import os
import subprocess
import sys

from emkeel.init import APPEND_LINES, Config, _files


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True)


def managed_paths() -> set[str]:
    """The set of paths Emkeel owns (static — independent of config values)."""
    return set(_files(Config()).keys()) | set(APPEND_LINES.keys())


def changed_files(base: str, run=_run) -> list[str]:
    r = run(["git", "diff", "--name-only", f"origin/{base}...HEAD"])
    return [f for f in r.stdout.splitlines() if f.strip()]


def main() -> int:
    branch = os.environ.get("EMKEEL_BRANCH", "")
    if not branch.startswith("emkeel-maint/"):
        print(f"OK: '{branch}' is not a maintenance branch; scope check N/A.")
        return 0

    base = os.environ.get("EMKEEL_BASE_REF") or "main"
    files = changed_files(base)
    managed = managed_paths()
    stray = [f for f in files if f not in managed]
    if stray:
        print("FAIL: an emkeel-maint PR may only touch Emkeel-managed files, but it also changes: "
              f"{', '.join(stray)}. Use a real ticket branch for code changes.", file=sys.stderr)
        return 1
    print(f"OK: maintenance PR touches {len(files)} file(s), all Emkeel-managed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
