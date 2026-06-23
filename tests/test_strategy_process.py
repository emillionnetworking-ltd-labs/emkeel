"""The /strategy process schema driven by the generic engine — non-skippable steps, real provenance."""

import pytest

from emkeel.process import PrereqError, advance, new_state, read_state, step_done
from emkeel.strategy import _do_advance, _do_status, strategy_process

TS = "2026-06-20T00:00:00Z"
SCHEMA = strategy_process()


def _walk_to(state, *steps_with_fields):
    for step, fields in steps_with_fields:
        advance(SCHEMA, state, step, fields, timestamp=TS)


def test_schema_is_the_seven_step_strategy_process():
    assert SCHEMA.name == "strategy"
    assert SCHEMA.names() == ["scaffolded", "researched", "proposed", "critiqued",
                              "checked", "presented", "approved"]


def test_cannot_reach_approved_by_skipping(tmp_path):
    st = new_state(SCHEMA)
    # jump straight to approved → refused (researched/proposed/… not done)
    with pytest.raises(PrereqError):
        advance(SCHEMA, st, "approved", {"approved_by": "operator"}, timestamp=TS)


# ── researched provenance (subsumes the research-provenance gap) ───────────────

def test_researched_refused_without_provenance():
    st = new_state(SCHEMA)
    advance(SCHEMA, st, "scaffolded", {"topic": "auth"}, timestamp=TS)
    with pytest.raises(PrereqError, match="provenance"):
        advance(SCHEMA, st, "researched", {}, timestamp=TS)                 # no sources, no internal_only
    with pytest.raises(PrereqError, match="provenance"):
        advance(SCHEMA, st, "researched", {"sources": ["just some prose"]}, timestamp=TS)  # not verifiable


def test_researched_accepts_external_url_source():
    st = new_state(SCHEMA)
    advance(SCHEMA, st, "scaffolded", {"topic": "auth"}, timestamp=TS)
    advance(SCHEMA, st, "researched", {"sources": ["https://pages.nist.gov/800-63b/"]}, timestamp=TS)
    assert step_done(st, "researched")


def test_researched_accepts_repo_fileline_source():
    st = new_state(SCHEMA)
    advance(SCHEMA, st, "scaffolded", {"topic": "auth"}, timestamp=TS)
    advance(SCHEMA, st, "researched", {"sources": ["src/auth/session.py:42"]}, timestamp=TS)
    assert step_done(st, "researched")


def test_researched_accepts_explicit_internal_only():
    st = new_state(SCHEMA)
    advance(SCHEMA, st, "scaffolded", {"topic": "auth"}, timestamp=TS)
    advance(SCHEMA, st, "researched", {"internal_only": True}, timestamp=TS)
    assert step_done(st, "researched")


# ── checked + the human gate at approved ───────────────────────────────────────

def test_checked_requires_recorded_pass():
    st = new_state(SCHEMA)
    _walk_to(st,
             ("scaffolded", {"topic": "auth"}),
             ("researched", {"internal_only": True}),
             ("proposed", {"options": ["jwt", "sessions"]}),
             ("critiqued", {"critique": "adversarial pass done"}))
    with pytest.raises(PrereqError, match="check_passed"):
        advance(SCHEMA, st, "checked", {"check_passed": False}, timestamp=TS)
    advance(SCHEMA, st, "checked", {"check_passed": True}, timestamp=TS)
    assert step_done(st, "checked")


def test_approved_requires_human_gate_field():
    st = new_state(SCHEMA)
    _walk_to(st,
             ("scaffolded", {"topic": "auth"}),
             ("researched", {"internal_only": True}),
             ("proposed", {"options": ["jwt", "sessions"]}),
             ("critiqued", {"critique": "x"}),
             ("checked", {"check_passed": True}),
             ("presented", {"presented_to": "operator"}))
    with pytest.raises(PrereqError, match="approved_by"):
        advance(SCHEMA, st, "approved", {}, timestamp=TS)                   # no human recorded → refused
    advance(SCHEMA, st, "approved", {"approved_by": "operator"}, timestamp=TS)
    assert st["state"] == "approved"


# ── the CLI driving the engine (end to end, on disk) ───────────────────────────

def test_cli_advance_and_status_on_disk(tmp_path, capsys):
    (tmp_path / "emkeel-governance/strategy").mkdir(parents=True)
    # skipping is refused via the CLI too
    assert _do_advance("researched", "auth", ["internal_only=true"], tmp_path) == 1   # scaffolded not done
    assert "REFUSED" in capsys.readouterr().err
    assert _do_advance("scaffolded", "auth", ["topic=auth"], tmp_path) == 0
    assert _do_advance("researched", "auth", ["internal_only=true"], tmp_path) == 0
    state = read_state(tmp_path / "emkeel-governance/strategy/auth.process.json")
    assert state["state"] == "researched"

    assert _do_status("auth", tmp_path) == 0
    out = capsys.readouterr().out
    assert "✓ scaffolded" in out and "✓ researched" in out and "· approved" in out


def test_cli_main_dispatch(tmp_path, monkeypatch, capsys):
    from emkeel.strategy import main
    (tmp_path / "emkeel-governance/strategy").mkdir(parents=True)
    monkeypatch.setenv("EMKEEL_REPO_DIR", str(tmp_path))
    assert main(["advance", "scaffolded", "auth", "--set=topic=auth"]) == 0
    assert main(["status", "auth"]) == 0
    assert "✓ scaffolded" in capsys.readouterr().out


def test_cli_advance_usage_and_errors(tmp_path, monkeypatch, capsys):
    from emkeel.strategy import main
    (tmp_path / "emkeel-governance/strategy").mkdir(parents=True)
    monkeypatch.setenv("EMKEEL_REPO_DIR", str(tmp_path))
    assert main(["advance"]) == 2                                  # no step → usage
    assert main(["advance", "bogus-step", "auth"]) == 2            # unknown step
    assert main(["advance", "scaffolded", "auth", "--set=badpair"]) == 2   # --set without '='
    assert main([]) == 2                                           # top-level usage


def test_cli_status_not_started(tmp_path, monkeypatch, capsys):
    from emkeel.strategy import main
    (tmp_path / "emkeel-governance/strategy").mkdir(parents=True)
    monkeypatch.setenv("EMKEEL_REPO_DIR", str(tmp_path))
    assert main(["status", "auth"]) == 0
    assert "process not started" in capsys.readouterr().out


# ── KEEL-104: a refinement resets the process — a prior `approved` never carries over ──

def test_reentering_first_step_resets_the_process():
    st = new_state(SCHEMA)
    # drive a full prior refinement to approved
    _walk_to(st,
             ("scaffolded", {"topic": "auth"}),
             ("researched", {"internal_only": True}),
             ("proposed", {"options": ["a", "b"]}),
             ("critiqued", {"critique": "x"}),
             ("checked", {"check_passed": True}),
             ("presented", {"presented_to": "op"}),
             ("approved", {"approved_by": "op"}))
    assert st["state"] == "approved" and step_done(st, "approved")
    # a NEW refinement re-enters scaffolded → CLEAN reset (the prior approved is gone)
    advance(SCHEMA, st, "scaffolded", {"topic": "auth"}, timestamp=TS)
    assert st["state"] == "scaffolded"
    assert step_done(st, "scaffolded") and not step_done(st, "approved")
    assert list(st["steps"]) == ["scaffolded"]
