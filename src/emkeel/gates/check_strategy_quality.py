"""Gate: every strategy doc must be grounded — it must pass `emkeel strategy check`.

Deterministic, runs in CI. A strategy with an unsourced option (or a missing required section) FAILS
the build, so an ungrounded/hallucinated strategy can't merge. Dormant when there are no strategy
docs. This is the hard half of Layer 2: the skill guides the research; this gate is the computed fact.
"""

from __future__ import annotations

import sys
from pathlib import Path

from emkeel.strategy import _do_check


def main() -> int:
    return _do_check("", Path("."))   # lints every emkeel-governance/strategy/*.md; 0 if clean/none, 1 if any fails


if __name__ == "__main__":
    sys.exit(main())
