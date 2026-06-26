"""Integration: the governed /strategy process can't certify a human approval that never happened.

The ECO-69 incident, end to end: a committed <topic>.process.json with a FORGED `approved` (no human
backing) must FAIL `check_strategy_process`; and a new refinement of an already-approved topic must RESET
the process (a prior `approved` never carries over). Exercises the real engine + the real gate.
"""

import emkeel.gates.check_strategy_process as gate
from emkeel.process import advance_on_disk, read_state, step_done
from emkeel.strategy import strategy_process

SDIR = "emkeel-governance/strategy"
TS = "2026-06-23T00:00:00Z"
KC = ["the pilot rejects it", "worse than the baseline"]
REALITY = {"case": "ECO-71", "method": "applied to one real case",
           "outcome": "pass", "evidence_ref": "https://example.com/pilot"}


def _drive(p, *steps):
    for name, fields in steps:
        advance_on_disk(strategy_process(), p, name, fields, timestamp=TS)


def _run_gate(tmp_path, monkeypatch, changed):
    monkeypatch.setattr(gate, "changed_files", lambda base, **k: list(changed))
    monkeypatch.setenv("EMKEEL_BASE_REF", "main")
    monkeypatch.setenv("EMKEEL_REPO_DIR", str(tmp_path))
    monkeypatch.delenv("EMKEEL_STRATEGY_DIR", raising=False)
    return gate.main()


def _scaffold(tmp_path, topic="satellites"):
    (tmp_path / SDIR).mkdir(parents=True, exist_ok=True)
    (tmp_path / SDIR / f"{topic}.md").write_text(f"# Strategy: {topic}\n")
    return tmp_path / SDIR / f"{topic}.process.json"


def test_forged_approved_fails_the_gate(tmp_path, monkeypatch, capsys):
    p = _scaffold(tmp_path)
    _drive(p,
           ("scaffolded", {"topic": "satellites", "kill_criteria": KC}),
           ("researched", {"sources": ["https://nist.gov/x"]}),
           ("proposed", {"options": ["a", "b"]}),
           ("critiqued", {"critique": "x"}),
           ("checked", {"check_passed": True}),
           ("validated", REALITY),
           ("presented", {"presented_to": "operador"}),
           ("approved", {"approved_by": "operador"}))     # forged: no human actually approved
    assert step_done(read_state(p), "approved")            # the file claims approval…
    assert _run_gate(tmp_path, monkeypatch, [f"{SDIR}/satellites.md"]) == 1   # …the gate refuses it
    assert "approved" in capsys.readouterr().err.lower()


def test_refinement_resets_a_prior_approval_then_passes_at_presented(tmp_path, monkeypatch):
    p = _scaffold(tmp_path)
    # a prior refinement was fully approved (e.g. ECO-64)…
    _drive(p,
           ("scaffolded", {"topic": "satellites", "kill_criteria": KC}),
           ("researched", {"internal_only": True}),
           ("proposed", {"options": ["a", "b"]}),
           ("critiqued", {"critique": "x"}),
           ("checked", {"check_passed": True}),
           ("validated", REALITY),
           ("presented", {"presented_to": "op"}),
           ("approved", {"approved_by": "op"}))
    # …a NEW refinement re-runs from scaffolded → the engine resets; approved does NOT carry over.
    _drive(p,
           ("scaffolded", {"topic": "satellites", "kill_criteria": KC}),
           ("researched", {"sources": ["https://fidoalliance.org/specs/"]}),
           ("proposed", {"options": ["c", "d"]}),
           ("critiqued", {"critique": "fresh adversarial pass"}),
           ("checked", {"check_passed": True}),
           ("validated", REALITY),
           ("presented", {"presented_to": "op"}))
    assert not step_done(read_state(p), "approved")        # the prior approval is gone
    assert _run_gate(tmp_path, monkeypatch, [f"{SDIR}/satellites.md"]) == 0   # clean, at presented → OK
