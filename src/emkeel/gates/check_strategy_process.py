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
from emkeel.strategy import (STRATEGY_DIR, _reality_validated, _repo_problem, _researched_provenance,
                            classify_source, strategy_process)


def strategy_docs_changed(files: list[str], strategy_dir: str) -> list[str]:
    """Changed `.md` files under strategy_dir (ignores .gitkeep / non-md / the .process.json sidecar)."""
    prefix = strategy_dir.rstrip("/") + "/"
    return [f for f in files if f.startswith(prefix) and f.endswith(".md")]


def _reality_gated(state: dict | None) -> bool:
    """True iff this state was created under a schema carrying the `validated` step (recorded in
    `steps_schema` at creation). Legacy states predate it → grandfathered, never retroactively broken."""
    return isinstance(state, dict) and "validated" in (state.get("steps_schema") or [])


def _state_step_names(state: dict | None) -> list[str]:
    """The ordered step universe for THIS state: its recorded `steps_schema`, else the legacy (pre-reality)
    schema — the current schema minus the `validated` step it predates. Keeps the bar + the
    coherence/ordering checks relative to the schema that actually created the state (back-compat)."""
    if isinstance(state, dict) and state.get("steps_schema"):
        return list(state["steps_schema"])
    return [s.name for s in strategy_process().steps if s.name != "validated"]


def required_done_steps(state: dict | None = None) -> list[str]:
    """Steps that must be `done` for a strategy to merge. The bar is `validated` for reality-gated states;
    legacy states (no recorded `validated` step) keep the pre-reality `checked` bar (grandfathered)."""
    names = _state_step_names(state)
    bar = "validated" if _reality_gated(state) else "checked"
    return names[: names.index(bar) + 1]


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
    bar = "validated" if _reality_gated(state) else "checked"
    missing = [s for s in required_done_steps(state) if not step_done(state, s)]
    if missing:
        return (f"{md} — the /strategy process hasn't reached '{bar}' (missing: {', '.join(missing)}). "
                "Run each step via `emkeel strategy advance` (the engine refuses to skip).")
    provenance = state.get("steps", {}).get("researched", {})
    ok, why = _researched_provenance(provenance)
    if not ok:
        return f"{md} — the 'researched' step lacks provenance: {why} (no silent skip of the research)."

    # REALITY GATE (KEEL-114): a reality-gated strategy must carry sound reality evidence at `validated`,
    # and approving DESPITE a failed reality test must be a recorded, conscious act. Deterministic — it
    # checks presence/structure/resolution, NEVER whether the outcome itself is 'good' (that's the human's
    # judgment at approval, exactly as approval is the human merge, not a self-written `approved_by`).
    if _reality_gated(state):
        reality = _reality_problem(state, target)
        if reality:
            return f"{md} — {reality}"

    # INVARIANT (KEEL-104): the committed record may NOT certify a human approval. `approved_by` is a
    # forgeable self-written field; the REAL human gate is the PR review + merge (branch protection
    # requires a human approving review). So a committed process caps at `presented` — `approved` is
    # granted by the merge, not pre-stamped in the file. A committed `approved` is a lie at CI time → FAIL.
    if step_done(state, "approved") or state.get("state") == "approved":
        return (f"{md} — the committed process claims 'approved', but a committed file can't certify a "
                "human approval the merge hasn't granted yet (the approving PR review IS the human gate). "
                "Stop at 'presented'; approval is the operator's review + merge, not a self-written field.")

    # COHERENCE: the done steps must be a contiguous prefix (no holes / out-of-order forgery) with
    # non-decreasing timestamps — reject a fabricated state that skipped a step or back-dated one.
    incoherent = _coherence_problem(state)
    if incoherent:
        return f"{md} — incoherent process state: {incoherent}"
    return None


def _reality_problem(state: dict, target: Path) -> str | None:
    """Structural validation of the `validated` step's reality evidence + the conscious-override rule.
    Deterministic; never judges the outcome value. A repo `evidence_ref` must resolve against the repo root
    (URLs were checked well-formed at advance; an external citation passes — the human confirms it)."""
    v = state.get("steps", {}).get("validated", {})
    ok, why = _reality_validated(v)
    if not ok:
        return f"the 'validated' step's reality evidence is incomplete: {why}."
    ref = str(v.get("evidence_ref", "")).strip()
    if classify_source(ref) == "repo":
        prob = _repo_problem(ref, target)
        if prob:
            return f"the 'validated' evidence_ref {ref!r} does not resolve: {prob}."
    # CONSCIOUS OVERRIDE: if reality did not cleanly pass and the process has proceeded toward approval
    # (`presented`), a `proceed_justification` MUST be on record — approving despite a failed reality test
    # is a deliberate act, never silent. The gate checks PRESENCE, never the justification's content.
    outcome = str(v.get("outcome", "")).strip().lower()
    if outcome in ("fail", "mixed") and step_done(state, "presented"):
        pj = state.get("steps", {}).get("presented", {}).get("proceed_justification")
        if not (isinstance(pj, str) and pj.strip()):
            return (f"reality outcome is '{outcome}', but proceeding to 'presented' toward approval requires a "
                    "recorded `proceed_justification` — approving despite a failed reality test must be a "
                    "deliberate, on-record act (record it on the 'presented' step)")
    return None


def _coherence_problem(state: dict) -> str | None:
    """None if the done steps form a contiguous prefix of THIS state's schema with monotonic timestamps."""
    names = _state_step_names(state)
    done = [n for n in names if step_done(state, n)]
    # contiguous prefix: the done set must equal the first len(done) steps (no gaps, no out-of-order)
    if done != names[: len(done)]:
        return f"steps done out of order / with holes ({done}); the engine advances strictly in sequence."
    stamps = [state["steps"][n].get("timestamp", "") for n in done]
    given = [s for s in stamps if s]
    if given != sorted(given):
        return "step timestamps are out of order (a step is dated before an earlier one)."
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
