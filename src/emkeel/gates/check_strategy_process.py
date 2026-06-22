"""Gate: a strategy doc change must carry its committed governed-process state (non-skippable steps).

Deterministic, runs in CI. The `/strategy` skill drives a state machine (emkeel.process): scaffolded →
researched → proposed → critiqued → checked → presented → approved. Without a gate reading that state, an
agent could skip a step (notably the web research) and still merge a strategy doc. This closes it:

When a PR touches `emkeel-governance/strategy/<topic>.md`, the matching `<topic>.process.json` MUST be
committed, have reached at least `checked` (every step up to it done), and its `researched` step MUST
carry provenance (a real source — URL / repo file:line — or an explicit `internal_only=true`). Otherwise
FAIL. N/A when the diff touches no strategy doc. Needs `fetch-depth: 0` for the base diff.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from emkeel.gates.check_maint_scope import changed_files
from emkeel.process import StateParseError, read_state, step_done
from emkeel.strategy import STRATEGY_DIR, _researched_provenance, strategy_process


def strategy_docs_changed(files: list[str], strategy_dir: str) -> list[str]:
    """Changed `.md` files under strategy_dir (ignores .gitkeep / non-md / the .process.json sidecar)."""
    prefix = strategy_dir.rstrip("/") + "/"
    return [f for f in files if f.startswith(prefix) and f.endswith(".md")]


def required_done_steps() -> list[str]:
    """Steps that must be `done` for a strategy to merge: everything up to AND including `checked`."""
    schema = strategy_process()
    return [s.name for s in schema.steps[: schema.index("checked") + 1]]


def check_doc(md: str, strategy_dir: str, target: Path) -> str | None:
    """None if `md`'s governed process is complete-enough to merge, else a FAIL reason."""
    proc = target / f"{md[: -len('.md')]}.process.json"      # emkeel-governance/strategy/<topic>.process.json
    if not proc.is_file():
        return (f"{md} changed but its governed-process state '{proc.as_posix()}' is missing — drive it "
                "with `emkeel strategy advance <step> <topic> …` and commit the .process.json.")
    try:
        state = read_state(proc)
    except StateParseError as e:
        return f"{md}: cannot parse {proc.as_posix()} ({e})."
    if not isinstance(state, dict):
        return f"{md}: {proc.as_posix()} is not a valid process state."
    missing = [s for s in required_done_steps() if not step_done(state, s)]
    if missing:
        return (f"{md} — the /strategy process hasn't reached 'checked' (missing: {', '.join(missing)}). "
                "Run each step via `emkeel strategy advance` (the engine refuses to skip).")
    provenance = state.get("steps", {}).get("researched", {})
    ok, why = _researched_provenance(provenance)
    if not ok:
        return f"{md} — the 'researched' step lacks provenance: {why} (no silent skip of the research)."
    return None


def main() -> int:
    base = os.environ.get("EMKEEL_BASE_REF") or "main"
    strategy_dir = os.environ.get("EMKEEL_STRATEGY_DIR", STRATEGY_DIR)
    target = Path(os.environ.get("EMKEEL_REPO_DIR", "."))

    touched = strategy_docs_changed(changed_files(base), strategy_dir)
    if not touched:
        print(f"OK: PR changes no strategy doc under {strategy_dir}/ — strategy-process check N/A.")
        return 0

    ok = True
    for md in touched:
        problem = check_doc(md, strategy_dir, target)
        if problem:
            ok = False
            print(f"FAIL: {problem}", file=sys.stderr)
        else:
            print(f"OK: {md} — governed process reached 'checked' with researched provenance.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
