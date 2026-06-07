"""Review-assist: assemble grounded inputs for a per-criterion PR review.

NOT a gate. AI judgment is advisory, not deterministic — so this never blocks CI.
This deterministic helper extracts the ticket's Acceptance Criteria so the reviewer
(AI and/or human) addresses each written objective explicitly, instead of vibes.
The verdict (met / not-met / unsure) is the reviewer's job; the human approves the merge.

CLI:  python -m emkeel.review <TICKET-KEY>
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from emkeel.gates.check_plan_present import spec_path_for

_HEADING_RE = re.compile(r"^#{1,6}\s*acceptance\s+criteria\s*$", re.IGNORECASE)


def extract_criteria(spec_text: str) -> list[str]:
    """Return the bullet items under the 'Acceptance Criteria' heading, in order."""
    out: list[str] = []
    in_section = False
    for line in spec_text.splitlines():
        stripped = line.strip()
        if _HEADING_RE.match(stripped):
            in_section = True
            continue
        if in_section:
            if stripped.startswith("#"):  # next section ends the block
                break
            if stripped.startswith(("- ", "* ")):
                out.append(stripped[2:].strip())
    return out


def render_review_template(key: str, criteria: list[str]) -> str:
    """A markdown template the reviewer fills with a per-criterion verdict."""
    lines = [
        f"# Review — {key}",
        "",
        "Per-criterion verdict (met / not-met / unsure) + evidence from the diff.",
        "",
    ]
    if not criteria:
        lines.append("_No acceptance criteria found in the spec._")
    for i, c in enumerate(criteria, 1):
        lines += [f"## AC{i}: {c}", "- verdict: ", "- evidence: ", ""]
    lines += [
        "## Concerns",
        "- ",
        "",
        "## Uncovered by tests (ratchet -> file a test)",
        "- ",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("usage: python -m emkeel.review <TICKET-KEY>", file=sys.stderr)
        return 2
    key = argv[0]
    specs_dir = Path(os.environ.get("EMKEEL_SPECS_DIR", "emkeel-governance/specs"))
    path = spec_path_for(key, specs_dir)
    if not path.is_file():
        print(f"FAIL: spec not found for {key}: {path}", file=sys.stderr)
        return 1
    criteria = extract_criteria(path.read_text(encoding="utf-8"))
    print(render_review_template(key, criteria))
    return 0


if __name__ == "__main__":
    sys.exit(main())
