"""Gate: every strategy doc must be grounded — it must pass `emkeel strategy check`.

Deterministic, runs in CI. A strategy whose option has an unsourced cell, a `file:line` that doesn't
resolve, or a malformed URL FAILS the build, so an ungrounded/hallucinated strategy can't merge.
External (non-resolvable) citations are surfaced as WARN for the human, never a silent pass. Dormant
when there are no strategy docs. The hard half of Layer 2: the skill guides research; this is the fact.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from emkeel.strategy import _do_check


def main() -> int:
    # Repo root is injectable (EMKEEL_REPO_DIR) so file:line sources resolve against it — testable with
    # fixtures, hermetic by default. Lints every emkeel-governance/strategy/*.md; 0 if clean/none, 1 if any fails.
    return _do_check("", Path(os.environ.get("EMKEEL_REPO_DIR", ".")))


if __name__ == "__main__":
    sys.exit(main())
