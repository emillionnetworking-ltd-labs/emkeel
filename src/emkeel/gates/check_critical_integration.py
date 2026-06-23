"""Gate: a change to a CRITICAL / cross-cutting surface must ship an INTEGRATION test.

Deterministic, runs in CI. Born from the KEEL-93/94 incident: the credential-isolation change broke
`emkeel jira create` (it depended on direnv) and NO test caught it — the coverage was unit-only, with no
end-to-end test of the creds→create flow. This makes the discipline mechanical: if a PR's diff touches a
critical surface (the manifest below), it MUST also add/change a test under `tests/integration/` that
exercises the affected end-to-end flow. Otherwise FAIL — exactly as `check_plan_present` requires a spec
on a `feat/` branch. N/A when no critical surface is touched. Needs `fetch-depth: 0` for the base diff.
"""

from __future__ import annotations

import os
import sys

from emkeel.gates.check_maint_scope import changed_files

# The MANIFEST of critical / cross-cutting surfaces — explicit on purpose (and unit-tested).
CRITICAL_FILES = (
    "src/emkeel/jira.py",          # credentials + Jira ticket creation/transition
    "src/emkeel/isolation.py",     # per-repo isolation + the PreToolUse guard
    "src/emkeel/init.py",          # distribution: _files / scaffold / the _agents_md agent contract
    "src/emkeel/update.py",        # distribution: wiring refresh + drift detection
    "src/emkeel/ship.py",          # distribution: the scope-gated maintenance-lane ship
)
CRITICAL_DIR_PREFIXES = (
    "src/emkeel/gates/",           # any CI gate (the enforcement layer itself)
)
INTEGRATION_PREFIX = "tests/integration/"


def is_critical(path: str) -> bool:
    """True if `path` is a critical / cross-cutting surface per the manifest."""
    p = path.strip()
    return p in CRITICAL_FILES or any(p.startswith(d) for d in CRITICAL_DIR_PREFIXES)


def is_integration_test(path: str) -> bool:
    return path.strip().startswith(INTEGRATION_PREFIX)


def main() -> int:
    base = os.environ.get("EMKEEL_BASE_REF") or "main"
    files = changed_files(base)

    critical = sorted({f for f in files if is_critical(f)})
    if not critical:
        print("OK: no critical surface touched — integration check N/A.")
        return 0

    if any(is_integration_test(f) for f in files):
        print(f"OK: critical surface(s) changed ({', '.join(critical)}) WITH an integration test "
              f"under {INTEGRATION_PREFIX}.")
        return 0

    print(
        f"FAIL: this PR changes a critical/cross-cutting surface ({', '.join(critical)}) but adds NO "
        f"integration test under `{INTEGRATION_PREFIX}`. A critical change must come with an end-to-end "
        "test of the affected flow (the lesson of KEEL-93/94: a unit-only change broke `emkeel jira "
        "create` and nothing caught it). Add/extend a `tests/integration/` test that exercises it.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
