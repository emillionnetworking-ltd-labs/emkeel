"""Gate: a feature's spec must declare Acceptance Criteria.

Deterministic, runs in CI. For a feature branch (``feat/``), the spec
``emkeel-governance/specs/<KEY>.md`` must contain a non-empty "Acceptance Criteria"
section. This is the prerequisite for the AI/human review step: you can only verify
objectives that were written down. "done" = the section exists with content, not a flag.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from emkeel.gates.check_plan_present import find_ticket_key, spec_path_for, spec_required

_HEADING_RE = re.compile(r"^#{1,6}\s*acceptance\s+criteria\s*$", re.IGNORECASE | re.MULTILINE)


def has_acceptance_criteria(text: str) -> bool:
    """True if the text has an 'Acceptance Criteria' heading followed by some content."""
    m = _HEADING_RE.search(text)
    if not m:
        return False
    for line in text[m.end():].splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):  # next heading reached → section is empty
            return False
        return True  # found real content under the heading
    return False


def main() -> int:
    branch = os.environ.get("EMKEEL_BRANCH", "")
    specs_dir = Path(os.environ.get("EMKEEL_SPECS_DIR", "emkeel-governance/specs"))

    if not spec_required(branch):
        print(f"OK: branch '{branch}' is not a feature; no criteria required.")
        return 0

    key = find_ticket_key(branch)
    if not key:
        print(f"FAIL: feature branch '{branch}' has no ticket key.", file=sys.stderr)
        return 1

    path = spec_path_for(key, specs_dir)
    if not path.is_file():
        print(f"FAIL: spec missing for {key}: {path}", file=sys.stderr)
        return 1

    if has_acceptance_criteria(path.read_text(encoding="utf-8")):
        print(f"OK: {key} spec declares Acceptance Criteria.")
        return 0

    print(
        f"FAIL: {key} spec has no non-empty 'Acceptance Criteria' section ({path}).",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
