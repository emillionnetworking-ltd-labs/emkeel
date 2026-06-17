"""Gate: a feature that serves a strategy must ACKNOWLEDGE how it aligns, not just link it.

Deterministic, runs in CI. `check_strategy_link` makes a feature spec point at its north star
(`Strategy: <area>`); this gate tightens the gap behind that pointer: when the link is a real strategy,
the spec must carry a non-empty "Alignment" section that spells out which north-star decisions/constraints
the feature implements or touches. The gate is purely SYNTACTIC — it requires the section to exist and
have content; whether the content is *true* is judged by the human at the PR (validating that semantically
would be AI judging AI, which violates adopt-and-thin).

Scope mirrors the siblings: feature branches only; DORMANT until a strategy exists; `Strategy: none`
(deliberate standalone) needs no Alignment. Config: EMKEEL_STRATEGY_DIR / EMKEEL_SPECS_DIR / EMKEEL_BRANCH.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from emkeel.gates.check_acceptance_criteria import has_section
from emkeel.gates.check_plan_present import find_ticket_key, spec_path_for, spec_required
from emkeel.gates.check_strategy_link import strategy_link


def main() -> int:
    branch = os.environ.get("EMKEEL_BRANCH", "")
    specs_dir = Path(os.environ.get("EMKEEL_SPECS_DIR", "emkeel-governance/specs"))
    strategy_dir = Path(os.environ.get("EMKEEL_STRATEGY_DIR", "emkeel-governance/strategy"))

    if not spec_required(branch):
        print(f"OK: branch '{branch}' is not a feature; no alignment required.")
        return 0

    # Dormant until a strategy exists (protects emkeel itself + repos not using strategies).
    strategies = sorted(p.stem for p in strategy_dir.glob("*.md")) if strategy_dir.is_dir() else []
    if not strategies:
        print(f"OK: no strategies defined yet ({strategy_dir}/ empty) — gate dormant.")
        return 0

    key = find_ticket_key(branch)
    if not key:
        print(f"OK: feature branch '{branch}' has no ticket key — deferred to check_plan_present.")
        return 0

    spec = spec_path_for(key, specs_dir)
    if not spec.is_file():
        # check_plan_present already FAILs the missing spec; don't duplicate that failure.
        print(f"OK: no spec for {key} yet — deferred to check_plan_present.")
        return 0

    declared = strategy_link(spec.read_text(encoding="utf-8"))
    if not declared:
        # check_strategy_link already FAILs the missing link; don't duplicate.
        print(f"OK: {key} declares no strategy link — deferred to check_strategy_link.")
        return 0
    if declared.lower() == "none":
        print(f"OK: {key} declares Strategy: none (standalone) — no alignment to acknowledge.")
        return 0

    if has_section(spec.read_text(encoding="utf-8"), "alignment"):
        print(f"OK: {key} acknowledges its alignment to strategy '{declared}'.")
        return 0

    print(
        f"FAIL: {key} declares `Strategy: {declared}` but its spec ({spec}) has no non-empty "
        "'Alignment' section. Add an `## Alignment` section listing which north-star decisions/"
        "constraints this feature implements or touches (the human judges the content at the PR).",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
