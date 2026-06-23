"""Generic governed-process engine — prereq-gated, non-skippable steps as a state machine.

A PROCESS is a schema of ordered steps. Each step may require fields (evidence to record) and gate on
the current state and/or on the payload being recorded. The engine REFUSES to advance into a step whose
prerequisite — the previous step done, plus any per-step predicate — isn't met. So "skipping a step"
does not exist by construction: the engine is the mechanism, not prose + an exit gate.

State is JSON on disk (the single source of truth), written under an `fcntl.flock` lock. This reuses the
proven lifecycle pattern (em-development-framework `forge/tools/_state_machine.py`: schema-defined state,
pure transitions with `evaluate_prereq`, lock-guarded writes, lib + thin CLI) — but stdlib-only to keep
emkeel zero-dependency: JSON instead of PyYAML.

GENERIC: nothing here is hardcoded to a particular skill. A skill declares its own `ProcessSchema` (see
`emkeel.strategy` for the first adopter) and drives `advance` / `read_state` / `evaluate_prereq`.
"""

from __future__ import annotations

import errno
import fcntl
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

LOCK_TIMEOUT_SECONDS = 5.0


class PrereqError(Exception):
    """Raised when an advance is refused (prerequisite not met / required evidence missing)."""


class LockTimeout(Exception):
    """Raised when the state lock can't be acquired within the timeout (another writer holds it)."""


class StateParseError(Exception):
    """Raised when a state file on disk is present but unparseable."""


# ---------- Schema (pure data a skill declares) ----------

@dataclass(frozen=True)
class Step:
    """One step of a process.

    - `requires`: field keys that MUST be present (and non-empty) in the advance payload — the evidence
      that the step actually happened (no silent skip).
    - `prereq`: optional predicate on the CURRENT state (beyond "previous step done"), e.g. a recorded
      human gate. `prereq_msg` is shown on refusal.
    - `validate`: optional predicate on the PAYLOAD being recorded → (ok, msg), e.g. research provenance.
    """
    name: str
    requires: tuple[str, ...] = ()
    prereq: Callable[[dict], bool] | None = None
    prereq_msg: str = ""
    validate: Callable[[dict], tuple[bool, str]] | None = None


@dataclass(frozen=True)
class ProcessSchema:
    name: str
    steps: tuple[Step, ...]

    def names(self) -> list[str]:
        return [s.name for s in self.steps]

    def index(self, step_name: str) -> int:
        for i, s in enumerate(self.steps):
            if s.name == step_name:
                return i
        raise KeyError(f"no step {step_name!r} in process {self.name!r} (have: {self.names()})")

    def step(self, step_name: str) -> Step:
        return self.steps[self.index(step_name)]


# ---------- Pure state model (no I/O) ----------

def new_state(schema: ProcessSchema) -> dict:
    return {"process": schema.name, "state": None, "steps": {}}


def step_done(state: dict, name: str) -> bool:
    return bool(state.get("steps", {}).get(name, {}).get("done") is True)


def current_state(state: dict) -> str | None:
    return state.get("state")


def _missing(state: dict, fields: dict, step: Step) -> list[str]:
    return [k for k in step.requires if k not in fields or fields[k] in (None, "", [], {})]


def evaluate_prereq(schema: ProcessSchema, state: dict, step_name: str) -> tuple[bool, str]:
    """True (+empty msg) if `step_name` may be advanced into now: the previous step is done AND the
    step's own `prereq(state)` predicate holds. This is what makes skipping impossible."""
    idx = schema.index(step_name)
    if idx > 0:
        prev = schema.steps[idx - 1].name
        if not step_done(state, prev):
            return False, f"step '{step_name}' requires the previous step '{prev}' to be done first"
    step = schema.steps[idx]
    if step.prereq is not None and not step.prereq(state):
        return False, step.prereq_msg or f"prerequisite for step '{step_name}' not met"
    return True, ""


def advance(schema: ProcessSchema, state: dict, step_name: str,
            fields: dict | None = None, timestamp: str | None = None) -> dict:
    """Pure in-RAM transition: re-check prereq + required evidence + payload validation, then mark the
    step done and move `state` forward. Raises PrereqError on any refusal. No disk I/O."""
    fields = dict(fields or {})
    if schema.index(step_name) == 0 and state.get("steps"):
        # Re-entering the FIRST step restarts the process — a new run/refinement starts CLEAN and never
        # inherits prior steps (notably a prior `approved`). The engine never auto-advances; a stale
        # approval can't survive into a fresh refinement.
        state["steps"] = {}
        state["state"] = None
    ok, msg = evaluate_prereq(schema, state, step_name)
    if not ok:
        raise PrereqError(msg)
    step = schema.step(step_name)
    miss = _missing(state, fields, step)
    if miss:
        raise PrereqError(f"step '{step_name}' requires field(s) {miss} (the evidence it happened)")
    if step.validate is not None:
        vok, vmsg = step.validate(fields)
        if not vok:
            raise PrereqError(f"step '{step_name}': {vmsg}")
    entry = state.setdefault("steps", {}).setdefault(step_name, {})
    entry["done"] = True
    entry["timestamp"] = timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry.update(fields)
    state["state"] = step_name
    return state


# ---------- Disk layer (lock-guarded; state on disk = the truth) ----------

class _ProcessLock:
    """fcntl.flock on the state file. 'exclusive' for writers, 'shared' for readers; raises LockTimeout
    if it can't be acquired within `timeout` seconds (another agent holds it)."""

    def __init__(self, path: Path, mode: str = "exclusive", timeout: float = LOCK_TIMEOUT_SECONDS):
        self.path = Path(path)
        self.mode = mode
        self.timeout = timeout
        self._fh = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("a+", encoding="utf-8")
        flag = (fcntl.LOCK_EX if self.mode == "exclusive" else fcntl.LOCK_SH) | fcntl.LOCK_NB
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                fcntl.flock(self._fh.fileno(), flag)
                return self
            except OSError as e:
                if e.errno not in (errno.EAGAIN, errno.EACCES):
                    raise
                if time.monotonic() > deadline:
                    self._fh.close()
                    self._fh = None
                    raise LockTimeout(f"could not acquire {self.mode} lock on {self.path} "
                                      f"within {self.timeout}s (another agent holds it)")
                time.sleep(0.02)

    def __exit__(self, *exc):
        if self._fh is not None:
            try:
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
            finally:
                self._fh.close()
            self._fh = None
        return False


def load_state(path: Path) -> dict | None:
    """Read the state JSON (None if the file doesn't exist). Raises StateParseError on garbage.
    Does NOT lock — use `read_state` for a lock-guarded read."""
    path = Path(path)
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return None
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError) as e:
        raise StateParseError(f"cannot parse state file {path}: {e}")
    if not isinstance(data, dict):
        raise StateParseError(f"state file {path} root is not an object")
    return data


def save_state(path: Path, state: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def read_state(path: Path, timeout: float = LOCK_TIMEOUT_SECONDS) -> dict | None:
    """Lock-guarded (shared) read of the state file."""
    path = Path(path)
    if not path.is_file():
        return None
    with _ProcessLock(path, mode="shared", timeout=timeout):
        return load_state(path)


def advance_on_disk(schema: ProcessSchema, path: Path, step_name: str,
                    fields: dict | None = None, timestamp: str | None = None,
                    timeout: float = LOCK_TIMEOUT_SECONDS) -> dict:
    """Lock-guarded (exclusive) advance: load → advance (re-checks prereqs) → save. The disk is the
    single source of truth; the lock serializes concurrent writers. Raises PrereqError if refused."""
    path = Path(path)
    with _ProcessLock(path, mode="exclusive", timeout=timeout):
        state = load_state(path)
        if state is None:
            state = new_state(schema)
        state = advance(schema, state, step_name, fields=fields, timestamp=timestamp)
        save_state(path, state)
        return state
