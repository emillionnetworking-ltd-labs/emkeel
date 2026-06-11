"""Gate: a feature must declare which strategy it serves (once strategies are in use).

Deterministic, runs in CI. This is the anti-"strategy-drift" gate: once any strategy exists
under `emkeel-governance/strategy/`, every feature spec must carry a `Strategy: <slug>` line
pointing to an existing strategy file (or `Strategy: none` for a deliberate standalone). It is
DORMANT until the first strategy is created, so repos not using strategies are unaffected.
"done" = the strategy link is real, not a self-attested flag.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from emkeel.gates.check_plan_present import spec_path_for, spec_required
from emkeel.gates.check_ticket_link import find_ticket_key

STRATEGY_RE = re.compile(r"^\s*Strategy:\s*(\S+)", re.MULTILINE | re.IGNORECASE)


def strategy_link(spec_text: str) -> str | None:
    """The declared strategy slug (or 'none'), or None if the spec doesn't declare one."""
    m = STRATEGY_RE.search(spec_text or "")
    return m.group(1).strip() if m else None


def main() -> int:
    branch = os.environ.get("EMKEEL_BRANCH", "")
    specs_dir = Path(os.environ.get("EMKEEL_SPECS_DIR", "emkeel-governance/specs"))
    strategy_dir = Path(os.environ.get("EMKEEL_STRATEGY_DIR", "emkeel-governance/strategy"))

    if not spec_required(branch):
        print(f"OK: branch '{branch}' is not a feature; no strategy link required.")
        return 0

    strategies = sorted(p.stem for p in strategy_dir.glob("*.md")) if strategy_dir.is_dir() else []
    if not strategies:
        print(f"OK: no strategies defined yet ({strategy_dir}/ empty) — gate dormant.")
        return 0

    key = find_ticket_key(branch)
    if not key:
        print(f"FAIL: feature branch '{branch}' has no ticket key.", file=sys.stderr)
        return 1

    spec = spec_path_for(key, specs_dir)
    if not spec.is_file():
        print(f"FAIL: feature {key} has no spec (needed for the Strategy link): {spec}", file=sys.stderr)
        return 1

    declared = strategy_link(spec.read_text(encoding="utf-8"))
    if not declared:
        print(f"FAIL: {key} must declare a strategy. Add a line `Strategy: <name>` to {spec} "
              f"(one of: {', '.join(strategies)} — or `none` for a deliberate standalone).",
              file=sys.stderr)
        return 1
    if declared.lower() == "none":
        print(f"OK: {key} explicitly declares Strategy: none (standalone).")
        return 0
    if declared not in strategies:
        print(f"FAIL: {key} references Strategy '{declared}' but {strategy_dir}/{declared}.md "
              f"does not exist. Known strategies: {', '.join(strategies)}.", file=sys.stderr)
        return 1

    print(f"OK: {key} follows strategy '{declared}'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
