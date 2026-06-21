"""Tests for the generic governed-process engine (the mechanism that makes a step non-skippable)."""

import pytest

from emkeel.process import (
    LockTimeout,
    PrereqError,
    ProcessSchema,
    StateParseError,
    Step,
    _ProcessLock,
    advance,
    advance_on_disk,
    current_state,
    evaluate_prereq,
    load_state,
    new_state,
    read_state,
    save_state,
    step_done,
)

# A tiny 3-step process: a → b (requires evidence) → c (gated on a state predicate).
SCHEMA = ProcessSchema("demo", (
    Step("a"),
    Step("b", requires=("note",)),
    Step("c", prereq=lambda s: s["steps"]["b"].get("note") == "ok",
         prereq_msg="c requires step b's note to be 'ok'"),
))

TS = "2026-06-20T00:00:00Z"


# ── refuse to skip (the whole point) ───────────────────────────────────────────

def test_advance_into_second_step_without_first_is_refused():
    st = new_state(SCHEMA)
    with pytest.raises(PrereqError, match="requires the previous step 'a'"):
        advance(SCHEMA, st, "b", {"note": "ok"}, timestamp=TS)


def test_cannot_jump_to_last_step():
    st = new_state(SCHEMA)
    with pytest.raises(PrereqError):
        advance(SCHEMA, st, "c", timestamp=TS)         # a and b not done → refused


def test_sequential_advance_succeeds():
    st = new_state(SCHEMA)
    advance(SCHEMA, st, "a", timestamp=TS)
    assert step_done(st, "a") and current_state(st) == "a"
    advance(SCHEMA, st, "b", {"note": "ok"}, timestamp=TS)
    assert current_state(st) == "b" and st["steps"]["b"]["note"] == "ok"
    advance(SCHEMA, st, "c", timestamp=TS)
    assert current_state(st) == "c"


# ── required evidence + payload validation ─────────────────────────────────────

def test_missing_required_field_is_refused():
    st = new_state(SCHEMA)
    advance(SCHEMA, st, "a", timestamp=TS)
    with pytest.raises(PrereqError, match="requires field"):
        advance(SCHEMA, st, "b", {}, timestamp=TS)     # 'note' missing


def test_empty_required_field_counts_as_missing():
    st = new_state(SCHEMA)
    advance(SCHEMA, st, "a", timestamp=TS)
    with pytest.raises(PrereqError):
        advance(SCHEMA, st, "b", {"note": ""}, timestamp=TS)


def test_state_predicate_prereq_is_enforced():
    st = new_state(SCHEMA)
    advance(SCHEMA, st, "a", timestamp=TS)
    advance(SCHEMA, st, "b", {"note": "nope"}, timestamp=TS)   # b done, but note != 'ok'
    with pytest.raises(PrereqError, match="note to be 'ok'"):
        advance(SCHEMA, st, "c", timestamp=TS)


def test_validate_hook_rejects_bad_payload():
    schema = ProcessSchema("v", (
        Step("only", validate=lambda f: (f.get("n", 0) > 0, "n must be > 0")),
    ))
    st = new_state(schema)
    with pytest.raises(PrereqError, match="n must be > 0"):
        advance(schema, st, "only", {"n": 0}, timestamp=TS)
    advance(schema, st, "only", {"n": 5}, timestamp=TS)        # passes
    assert step_done(st, "only")


def test_evaluate_prereq_returns_reason():
    ok, msg = evaluate_prereq(SCHEMA, new_state(SCHEMA), "b")
    assert ok is False and "previous step 'a'" in msg


# ── disk is the source of truth (lock-guarded) ─────────────────────────────────

def test_advance_on_disk_persists_and_reads_back(tmp_path):
    p = tmp_path / "state.json"
    advance_on_disk(SCHEMA, p, "a", timestamp=TS)
    advance_on_disk(SCHEMA, p, "b", {"note": "ok"}, timestamp=TS)
    on_disk = read_state(p)
    assert on_disk["state"] == "b" and on_disk["steps"]["a"]["done"] is True
    assert on_disk["steps"]["b"]["note"] == "ok"


def test_advance_on_disk_refuses_skip_too(tmp_path):
    p = tmp_path / "state.json"
    with pytest.raises(PrereqError):
        advance_on_disk(SCHEMA, p, "b", {"note": "ok"}, timestamp=TS)   # 'a' not done on disk
    assert read_state(p) is None or read_state(p)["state"] is None       # nothing written


def test_read_state_absent_is_none(tmp_path):
    assert read_state(tmp_path / "missing.json") is None


def test_load_state_garbage_raises(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{ not json", encoding="utf-8")
    with pytest.raises(StateParseError):
        load_state(p)


def test_load_state_non_object_raises(tmp_path):
    p = tmp_path / "arr.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(StateParseError):
        load_state(p)


def test_exclusive_lock_is_mutually_exclusive(tmp_path):
    p = tmp_path / "state.json"
    save_state(p, new_state(SCHEMA))
    with _ProcessLock(p, mode="exclusive", timeout=0.2):
        with pytest.raises(LockTimeout):
            with _ProcessLock(p, mode="exclusive", timeout=0.2):
                pass


def test_shared_locks_coexist(tmp_path):
    p = tmp_path / "state.json"
    save_state(p, new_state(SCHEMA))
    with _ProcessLock(p, mode="shared", timeout=0.5):
        with _ProcessLock(p, mode="shared", timeout=0.5):
            pass   # two readers at once → fine
