"""The /strategy process schema driven by the generic engine — non-skippable steps, real provenance."""

import pytest

from emkeel.process import PrereqError, advance, new_state, read_state, step_done
from emkeel.strategy import _do_advance, _do_status, strategy_process

TS = "2026-06-20T00:00:00Z"
SCHEMA = strategy_process()

# reusable evidence so every walk satisfies the new required fields
KC = ["the pilot rejects it", "worse than the baseline"]                 # kill-criteria, declared up front
REALITY = {"case": "ECO-71", "method": "applied to one real case",       # the `validated` reality evidence
           "outcome": "pass", "evidence_ref": "https://example.com/pilot"}
CRIT = {"lens_discovery": "no sitemap; invisible to search", "lens_legal": "no cookie banner; GDPR risk",
        "lens_calibration": "thin vs the real ECO-71 render", "completeness": "no a11y lens — add it"}  # panel


def _walk_to(state, *steps_with_fields):
    for step, fields in steps_with_fields:
        advance(SCHEMA, state, step, fields, timestamp=TS)


def test_schema_is_the_eight_step_strategy_process():
    assert SCHEMA.name == "strategy"
    assert SCHEMA.names() == ["scaffolded", "researched", "proposed", "critiqued",
                              "checked", "validated", "presented", "approved"]


def test_cannot_reach_approved_by_skipping(tmp_path):
    st = new_state(SCHEMA)
    # jump straight to approved → refused (researched/proposed/… not done)
    with pytest.raises(PrereqError):
        advance(SCHEMA, st, "approved", {"approved_by": "operator"}, timestamp=TS)


# ── researched provenance (subsumes the research-provenance gap) ───────────────

def test_researched_refused_without_provenance():
    st = new_state(SCHEMA)
    advance(SCHEMA, st, "scaffolded", {"topic": "auth", "kill_criteria": KC}, timestamp=TS)
    with pytest.raises(PrereqError, match="provenance"):
        advance(SCHEMA, st, "researched", {}, timestamp=TS)                 # no sources, no internal_only
    with pytest.raises(PrereqError, match="provenance"):
        advance(SCHEMA, st, "researched", {"sources": ["just some prose"]}, timestamp=TS)  # not verifiable


def test_researched_accepts_external_url_source():
    st = new_state(SCHEMA)
    advance(SCHEMA, st, "scaffolded", {"topic": "auth", "kill_criteria": KC}, timestamp=TS)
    advance(SCHEMA, st, "researched", {"sources": ["https://pages.nist.gov/800-63b/"]}, timestamp=TS)
    assert step_done(st, "researched")


def test_researched_accepts_repo_fileline_source():
    st = new_state(SCHEMA)
    advance(SCHEMA, st, "scaffolded", {"topic": "auth", "kill_criteria": KC}, timestamp=TS)
    advance(SCHEMA, st, "researched", {"sources": ["src/auth/session.py:42"]}, timestamp=TS)
    assert step_done(st, "researched")


def test_researched_accepts_explicit_internal_only():
    st = new_state(SCHEMA)
    advance(SCHEMA, st, "scaffolded", {"topic": "auth", "kill_criteria": KC}, timestamp=TS)
    advance(SCHEMA, st, "researched", {"internal_only": True}, timestamp=TS)
    assert step_done(st, "researched")


# ── checked + the human gate at approved ───────────────────────────────────────

def test_checked_requires_recorded_pass():
    st = new_state(SCHEMA)
    _walk_to(st,
             ("scaffolded", {"topic": "auth", "kill_criteria": KC}),
             ("researched", {"internal_only": True}),
             ("proposed", {"options": ["jwt", "sessions"]}),
             ("critiqued", CRIT))
    with pytest.raises(PrereqError, match="check_passed"):
        advance(SCHEMA, st, "checked", {"check_passed": False}, timestamp=TS)
    advance(SCHEMA, st, "checked", {"check_passed": True}, timestamp=TS)
    assert step_done(st, "checked")


def test_approved_requires_human_gate_field():
    st = new_state(SCHEMA)
    _walk_to(st,
             ("scaffolded", {"topic": "auth", "kill_criteria": KC}),
             ("researched", {"internal_only": True}),
             ("proposed", {"options": ["jwt", "sessions"]}),
             ("critiqued", CRIT),
             ("checked", {"check_passed": True}),
             ("validated", REALITY),
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
    assert _do_advance("scaffolded", "auth", ["topic=auth", "kill_criteria=[worse,rejected]"], tmp_path) == 0
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
    assert main(["advance", "scaffolded", "auth", "--set=topic=auth", "--set=kill_criteria=[worse,rejected]"]) == 0
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
             ("scaffolded", {"topic": "auth", "kill_criteria": KC}),
             ("researched", {"internal_only": True}),
             ("proposed", {"options": ["a", "b"]}),
             ("critiqued", CRIT),
             ("checked", {"check_passed": True}),
             ("validated", REALITY),
             ("presented", {"presented_to": "op"}),
             ("approved", {"approved_by": "op"}))
    assert st["state"] == "approved" and step_done(st, "approved")
    # a NEW refinement re-enters scaffolded → CLEAN reset (the prior approved is gone)
    advance(SCHEMA, st, "scaffolded", {"topic": "auth", "kill_criteria": KC}, timestamp=TS)
    assert st["state"] == "scaffolded"
    assert step_done(st, "scaffolded") and not step_done(st, "approved")
    assert list(st["steps"]) == ["scaffolded"]


# ── KEEL-114: the reality bar (`validated`) + kill-criteria + the schema stamp ──

def test_scaffolded_requires_kill_criteria():
    st = new_state(SCHEMA)
    with pytest.raises(PrereqError, match="kill_criteria"):
        advance(SCHEMA, st, "scaffolded", {"topic": "auth"}, timestamp=TS)   # no abandon-conditions declared
    advance(SCHEMA, st, "scaffolded", {"topic": "auth", "kill_criteria": KC}, timestamp=TS)
    assert step_done(st, "scaffolded")


def _walk_to_checked(st):
    _walk_to(st,
             ("scaffolded", {"topic": "auth", "kill_criteria": KC}),
             ("researched", {"internal_only": True}),
             ("proposed", {"options": ["a", "b"]}),
             ("critiqued", CRIT),
             ("checked", {"check_passed": True}))


def test_validated_refused_without_reality_evidence():
    st = new_state(SCHEMA)
    _walk_to_checked(st)
    with pytest.raises(PrereqError, match="case|method|outcome|evidence_ref"):
        advance(SCHEMA, st, "validated", {}, timestamp=TS)        # reality can't be skipped to reach approved


def test_validated_refused_on_bad_outcome_enum():
    st = new_state(SCHEMA)
    _walk_to_checked(st)
    bad = {**REALITY, "outcome": "great"}                          # not one of pass|fail|mixed
    with pytest.raises(PrereqError, match="outcome"):
        advance(SCHEMA, st, "validated", bad, timestamp=TS)


def test_validated_refused_on_malformed_url_evidence():
    st = new_state(SCHEMA)
    _walk_to_checked(st)
    bad = {**REALITY, "evidence_ref": "https//missing-colon"}      # malformed URL → refused at advance
    with pytest.raises(PrereqError, match="evidence_ref"):
        advance(SCHEMA, st, "validated", bad, timestamp=TS)


def test_validated_accepts_a_recorded_fail_outcome():
    # a `fail` is a VALID, honest record — the engine never judges the outcome value.
    st = new_state(SCHEMA)
    _walk_to_checked(st)
    advance(SCHEMA, st, "validated", {**REALITY, "outcome": "fail"}, timestamp=TS)
    assert step_done(st, "validated")


def test_new_state_records_the_schema_shape():
    st = new_state(SCHEMA)
    assert st["steps_schema"] == SCHEMA.names() and "validated" in st["steps_schema"]


# ── KEEL-118: the critiqued multi-lens panel (engine baseline) ──

def _walk_to_proposed(st):
    _walk_to(st,
             ("scaffolded", {"topic": "auth", "kill_criteria": KC}),
             ("researched", {"internal_only": True}),
             ("proposed", {"options": ["a", "b"]}))


def test_critiqued_refuses_a_one_liner():
    st = new_state(SCHEMA); _walk_to_proposed(st)
    with pytest.raises(PrereqError, match="panel"):
        advance(SCHEMA, st, "critiqued", {"critique": "one prose line"}, timestamp=TS)   # no lenses


def test_critiqued_refuses_without_completeness_critic():
    st = new_state(SCHEMA); _walk_to_proposed(st)
    with pytest.raises(PrereqError, match="completeness"):
        advance(SCHEMA, st, "critiqued", {"lens_seo": "discovery gap"}, timestamp=TS)


def test_critiqued_accepts_one_lens_plus_completeness():
    st = new_state(SCHEMA); _walk_to_proposed(st)
    advance(SCHEMA, st, "critiqued", {"lens_seo": "x", "completeness": "none"}, timestamp=TS)
    assert step_done(st, "critiqued")
