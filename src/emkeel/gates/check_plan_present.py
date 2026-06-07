"""Gate: a *feature* change must carry its spec/plan.

Deterministic, runs in CI. If the branch is `feat/` (or `feature/`), it requires
`emkeel-governance/specs/<KEY>.md` to exist. Other types (chore/fix/docs) don't.
"done" = the spec exists, not a flag. Second link of ticket->spec traceability.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from emkeel.gates.check_ticket_link import find_ticket_key

FEATURE_PREFIXES = ("feat/", "feature/")


def spec_required(branch: str) -> bool:
    """True if the branch denotes a feature (and therefore requires a spec)."""
    b = branch.strip().lower()
    return any(b.startswith(p) for p in FEATURE_PREFIXES)


def spec_path_for(key: str, specs_dir: Path) -> Path:
    return specs_dir / f"{key}.md"


def main() -> int:
    branch = os.environ.get("EMKEEL_BRANCH", "")
    specs_dir = Path(os.environ.get("EMKEEL_SPECS_DIR", "emkeel-governance/specs"))

    if not spec_required(branch):
        print(f"OK: branch '{branch}' is not a feature; no spec required.")
        return 0

    key = find_ticket_key(branch)
    if not key:
        print(f"FAIL: feature branch '{branch}' has no ticket key.", file=sys.stderr)
        return 1

    path = spec_path_for(key, specs_dir)
    if path.is_file():
        print(f"OK: spec present for {key}: {path}")
        return 0

    print(
        f"FAIL: feature {key} has no spec. Create '{path}' before merging.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
