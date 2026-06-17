"""Gate: the governed north star (strategy/*.md) may only change on a dedicated strategy lane.

Deterministic, runs in CI. The approved strategy is the governed direction; if any feat/fix/chore/docs
PR could quietly edit (or delete) it, the code could bend the north to fit itself. So: whenever a PR's
diff touches a `strategy/*.md` file, the branch MUST be a deliberate strategy lane — `strategy/<TICKET>-slug`
(a `strategy/` prefix AND a ticket key). Otherwise FAIL. N/A when the diff touches no strategy doc.

The sibling of check_maint_scope: that one bounds WHICH files the emkeel-maint lane may touch; this one
bounds WHO may touch the north star. One direction only — it does not restrict the other files a
strategy/ branch carries (its ADR, spec, etc.). Needs `fetch-depth: 0` for the base diff.
"""

from __future__ import annotations

import os
import sys

from emkeel.gates.check_maint_scope import changed_files
from emkeel.gates.check_ticket_link import find_ticket_key


def strategy_docs_changed(files: list[str], strategy_dir: str) -> list[str]:
    """The changed `.md` files under strategy_dir (ADD/EDIT/DELETE). Ignores .gitkeep and non-md."""
    prefix = strategy_dir.rstrip("/") + "/"
    return [f for f in files if f.startswith(prefix) and f.endswith(".md")]


def main() -> int:
    branch = os.environ.get("EMKEEL_BRANCH", "")
    base = os.environ.get("EMKEEL_BASE_REF") or "main"
    strategy_dir = os.environ.get("EMKEEL_STRATEGY_DIR", "emkeel-governance/strategy")

    touched = strategy_docs_changed(changed_files(base), strategy_dir)
    if not touched:
        print(f"OK: PR changes no strategy doc under {strategy_dir}/ — strategy-change check N/A.")
        return 0

    # The north star is in the diff → this must be a deliberate strategy lane.
    if branch.startswith("strategy/") and find_ticket_key(branch):
        print(f"OK: deliberate north-star change on a strategy lane ('{branch}') — "
              f"touches {len(touched)} strategy doc(s): {', '.join(touched)}.")
        return 0

    print(
        f"FAIL: this PR changes the governed north star ({', '.join(touched)}) on branch '{branch}'. "
        "The strategy is only changed on a dedicated lane `strategy/<TICKET>-slug` (human-approved, "
        "its own ticket) — never inside a feature/fix. Move the strategy change there.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
