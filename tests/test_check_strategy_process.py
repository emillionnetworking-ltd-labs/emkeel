"""Tests for check_strategy_process — a strategy doc change must carry its committed, non-skippable process."""

import emkeel.gates.check_strategy_process as g
from emkeel.process import advance_on_disk, new_state, save_state
from emkeel.strategy import strategy_process

SDIR = "emkeel-governance/strategy"
TS = "2026-06-22T00:00:00Z"


def _strategy_dir(tmp_path):
    d = tmp_path / SDIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _md(tmp_path, topic="auth"):
    (_strategy_dir(tmp_path) / f"{topic}.md").write_text(f"# Strategy: {topic}\n")


KC = ["the pilot rejects it", "worse than the baseline"]
REALITY = {"case": "ECO-71", "method": "applied to one real case",
           "outcome": "pass", "evidence_ref": "https://example.com/pilot"}


def _drive_to_checked(tmp_path, topic="auth", *, sources=None, internal_only=False):
    """Drive the real engine to `checked`, recording provenance — the legitimate, complete path."""
    schema = strategy_process()
    p = tmp_path / SDIR / f"{topic}.process.json"
    advance_on_disk(schema, p, "scaffolded", {"topic": topic, "kill_criteria": KC}, timestamp=TS)
    fields = {"internal_only": True} if internal_only else {"sources": sources or ["https://nist.gov/x"]}
    advance_on_disk(schema, p, "researched", fields, timestamp=TS)
    advance_on_disk(schema, p, "proposed", {"options": ["a", "b"]}, timestamp=TS)
    advance_on_disk(schema, p, "critiqued", {"critique": "adversarial pass done"}, timestamp=TS)
    advance_on_disk(schema, p, "checked", {"check_passed": True}, timestamp=TS)
    return p


def _drive_to_validated(tmp_path, topic="auth", *, reality=None, **kw):
    """Drive to `validated` — the new merge bar (reality evidence recorded)."""
    p = _drive_to_checked(tmp_path, topic, **kw)
    advance_on_disk(strategy_process(), p, "validated", {**REALITY, **(reality or {})}, timestamp=TS)
    return p


def _run(tmp_path, monkeypatch, changed, deleted=()):
    monkeypatch.setattr(g, "changed_files", lambda base, **k: list(changed))
    monkeypatch.setattr(g, "deleted_files", lambda base, **k: list(deleted))
    monkeypatch.setenv("EMKEEL_BASE_REF", "main")
    monkeypatch.setenv("EMKEEL_REPO_DIR", str(tmp_path))
    monkeypatch.delenv("EMKEEL_STRATEGY_DIR", raising=False)
    return g.main()


# ── N/A + passing ──────────────────────────────────────────────────────────────

def test_na_when_no_strategy_doc_changed(tmp_path, monkeypatch):
    assert _run(tmp_path, monkeypatch, ["src/emkeel/cli.py", "README.md"]) == 0


def test_passes_with_process_at_validated_and_provenance(tmp_path, monkeypatch):
    _md(tmp_path)
    _drive_to_validated(tmp_path, sources=["https://pages.nist.gov/800-63b/", "src/auth/session.py:42"])
    assert _run(tmp_path, monkeypatch, [f"{SDIR}/auth.md"]) == 0


def test_passes_with_internal_only_provenance(tmp_path, monkeypatch):
    _md(tmp_path)
    _drive_to_validated(tmp_path, internal_only=True)         # no market dimension, declared explicitly
    assert _run(tmp_path, monkeypatch, [f"{SDIR}/auth.md"]) == 0


# ── failing cases ───────────────────────────────────────────────────────────────

def test_fails_when_process_json_missing(tmp_path, monkeypatch):
    _md(tmp_path)                                              # doc changed, but no .process.json committed
    assert _run(tmp_path, monkeypatch, [f"{SDIR}/auth.md"]) == 1


def test_fails_when_not_reached_checked(tmp_path, monkeypatch):
    _md(tmp_path)
    schema = strategy_process()
    p = tmp_path / SDIR / "auth.process.json"
    advance_on_disk(schema, p, "scaffolded", {"topic": "auth", "kill_criteria": KC}, timestamp=TS)
    advance_on_disk(schema, p, "researched", {"sources": ["https://nist.gov/x"]}, timestamp=TS)
    # stopped at researched → proposed/critiqued/checked not done
    assert _run(tmp_path, monkeypatch, [f"{SDIR}/auth.md"]) == 1


def test_fails_when_researched_lacks_provenance(tmp_path, monkeypatch):
    # a hand-forged state that reached 'checked' but whose researched step has NO real source.
    _md(tmp_path)
    p = tmp_path / SDIR / "auth.process.json"
    state = new_state(strategy_process())
    state["state"] = "validated"                              # reaches the bar so PROVENANCE is the trigger
    for s in ("scaffolded", "researched", "proposed", "critiqued", "checked", "validated"):
        state["steps"][s] = {"done": True, "timestamp": TS}
    state["steps"]["researched"]["sources"] = ["just some prose, not a real source"]
    state["steps"]["validated"].update(REALITY)
    save_state(p, state)
    assert _run(tmp_path, monkeypatch, [f"{SDIR}/auth.md"]) == 1


def test_fails_when_process_json_unparseable(tmp_path, monkeypatch):
    _md(tmp_path)
    (tmp_path / SDIR / "auth.process.json").write_text("{ not json")
    assert _run(tmp_path, monkeypatch, [f"{SDIR}/auth.md"]) == 1


def test_one_bad_doc_fails_the_build(tmp_path, monkeypatch):
    _md(tmp_path, "auth"); _drive_to_validated(tmp_path, "auth")   # auth is complete…
    _md(tmp_path, "cache")                                         # …cache has no process.json
    assert _run(tmp_path, monkeypatch, [f"{SDIR}/auth.md", f"{SDIR}/cache.md"]) == 1


def test_required_done_steps_is_through_checked():
    assert g.required_done_steps() == ["scaffolded", "researched", "proposed", "critiqued", "checked"]


# ── KEEL-114: the reality bar (`validated`), conscious override, and back-compat ──

def test_fails_when_reality_bar_not_reached(tmp_path, monkeypatch, capsys):
    # a reality-gated process that stops at `checked` (no `validated`) no longer merges.
    _md(tmp_path); _drive_to_checked(tmp_path)
    assert _run(tmp_path, monkeypatch, [f"{SDIR}/auth.md"]) == 1
    assert "validated" in capsys.readouterr().err.lower()


def test_fails_on_bad_reality_outcome_enum(tmp_path, monkeypatch, capsys):
    # the engine refuses a bad enum at advance, so forge it on disk → the GATE re-validates independently.
    _md(tmp_path)
    p = _drive_to_validated(tmp_path)
    import json
    st = json.loads(p.read_text())
    st["steps"]["validated"]["outcome"] = "great"            # not pass|fail|mixed (forged)
    p.write_text(json.dumps(st))
    assert _run(tmp_path, monkeypatch, [f"{SDIR}/auth.md"]) == 1
    assert "outcome" in capsys.readouterr().err.lower()


def test_fails_when_repo_evidence_ref_does_not_resolve(tmp_path, monkeypatch, capsys):
    _md(tmp_path)
    _drive_to_validated(tmp_path, reality={"evidence_ref": "src/emkeel/nope.py:999"})   # repo ref, unresolved
    assert _run(tmp_path, monkeypatch, [f"{SDIR}/auth.md"]) == 1
    assert "resolve" in capsys.readouterr().err.lower()


def test_passes_with_resolving_repo_evidence_ref(tmp_path, monkeypatch):
    _md(tmp_path)
    _drive_to_validated(tmp_path, reality={"evidence_ref": f"{SDIR}/auth.md:1"})  # resolves in the repo root
    assert _run(tmp_path, monkeypatch, [f"{SDIR}/auth.md"]) == 0


def test_fails_on_fail_outcome_without_proceed_justification(tmp_path, monkeypatch, capsys):
    # reality FAILED and the process proceeded to `presented` — approving despite it must be on record.
    _md(tmp_path)
    p = _drive_to_validated(tmp_path, reality={"outcome": "fail"})
    advance_on_disk(strategy_process(), p, "presented", {"presented_to": "operator"}, timestamp=TS)
    assert _run(tmp_path, monkeypatch, [f"{SDIR}/auth.md"]) == 1
    assert "proceed_justification" in capsys.readouterr().err.lower()


def test_passes_on_fail_outcome_with_proceed_justification(tmp_path, monkeypatch):
    # the conscious override: a recorded justification makes proceeding-despite-fail a deliberate act.
    _md(tmp_path)
    p = _drive_to_validated(tmp_path, reality={"outcome": "fail"})
    advance_on_disk(strategy_process(), p, "presented",
                    {"presented_to": "operator", "proceed_justification": "edge case; pivoting next sprint"},
                    timestamp=TS)
    assert _run(tmp_path, monkeypatch, [f"{SDIR}/auth.md"]) == 0


def test_back_compat_legacy_process_without_validated_passes_at_checked(tmp_path, monkeypatch):
    # a process created BEFORE the reality gate (no `steps_schema`, no `validated`) is grandfathered:
    # the bar stays `checked`, so touching the doc does not retroactively break it.
    _md(tmp_path)
    p = tmp_path / SDIR / "auth.process.json"
    state = new_state(strategy_process())
    del state["steps_schema"]                                 # legacy file predates the schema stamp
    state["state"] = "presented"
    for s in ("scaffolded", "researched", "proposed", "critiqued", "checked", "presented"):
        state["steps"][s] = {"done": True, "timestamp": TS}
    state["steps"]["researched"]["sources"] = ["https://nist.gov/x"]
    save_state(p, state)
    assert _run(tmp_path, monkeypatch, [f"{SDIR}/auth.md"]) == 0


def test_required_done_steps_reality_bar_when_gated():
    gated = {"steps_schema": g.strategy_process().names()}
    assert g.required_done_steps(gated)[-1] == "validated"


# ── KEEL-115: retiring a strategy (doc + sidecar deleted as a pair) ──

def test_clean_retiro_passes(tmp_path, monkeypatch, capsys):
    # the doc AND its sidecar are deleted (absent on disk) → a valid retiro → OK, not FAIL.
    _strategy_dir(tmp_path)                                   # dir exists; the files do not (deleted)
    md = f"{SDIR}/satellites.md"
    assert _run(tmp_path, monkeypatch,
                changed=[md], deleted=[md, f"{SDIR}/satellites.process.json"]) == 0
    assert "retired" in capsys.readouterr().out.lower()


def test_orphan_doc_deleted_but_sidecar_present_fails(tmp_path, monkeypatch, capsys):
    # the doc is deleted but its process sidecar survives → orphan (a process with no doc) → FAIL.
    _drive_to_validated(tmp_path, "satellites")              # writes satellites.process.json on disk
    md = f"{SDIR}/satellites.md"
    assert _run(tmp_path, monkeypatch, changed=[md], deleted=[md]) == 1   # sidecar NOT in deleted
    assert "orphan" in capsys.readouterr().err.lower()


def test_two_strategies_retired_together_pass(tmp_path, monkeypatch):
    # the real case: retire two strategies in one atomic PR, each as a doc+sidecar pair.
    _strategy_dir(tmp_path)
    a, b = f"{SDIR}/satellites.md", f"{SDIR}/satellite-builders.md"
    deleted = [a, b, f"{SDIR}/satellites.process.json", f"{SDIR}/satellite-builders.process.json"]
    assert _run(tmp_path, monkeypatch, changed=[a, b], deleted=deleted) == 0


def test_edit_path_unchanged_alongside_a_retiro(tmp_path, monkeypatch):
    # a retiro (OK) + an EDITED doc whose sidecar is missing (FAIL) → build fails; ADD/EDIT stays strict.
    _strategy_dir(tmp_path)
    retired = f"{SDIR}/satellites.md"
    _md(tmp_path, "cache")                                   # cache.md edited, no process.json committed
    assert _run(tmp_path, monkeypatch,
                changed=[retired, f"{SDIR}/cache.md"],
                deleted=[retired, f"{SDIR}/satellites.process.json"]) == 1


# ── KEEL-104: a committed 'approved' is never accepted (no self-certified human approval) ──

def _present_ts(tmp_path, topic="auth"):
    """Drive to `presented` (the legitimate terminal committed state in a lane PR)."""
    p = _drive_to_validated(tmp_path, topic)
    advance_on_disk(strategy_process(), p, "presented", {"presented_to": "operator"}, timestamp=TS)
    return p


def test_passes_at_presented(tmp_path, monkeypatch):
    _md(tmp_path); _present_ts(tmp_path)
    assert _run(tmp_path, monkeypatch, [f"{SDIR}/auth.md"]) == 0     # presented (not approved) → OK


def test_fails_when_committed_claims_approved(tmp_path, monkeypatch, capsys):
    # THE BUG: the committed file says approved while no human approved (the merge hasn't happened).
    _md(tmp_path)
    p = _present_ts(tmp_path)
    advance_on_disk(strategy_process(), p, "approved", {"approved_by": "operador"}, timestamp=TS)
    assert _run(tmp_path, monkeypatch, [f"{SDIR}/auth.md"]) == 1
    assert "approved" in capsys.readouterr().err.lower()


def test_fails_on_forged_approved_without_presented(tmp_path, monkeypatch):
    # a hand-forged state: approved 'done' but presented never happened (a hole) → incoherent + approved.
    _md(tmp_path)
    state = new_state(strategy_process())
    state["state"] = "approved"
    for s in ("scaffolded", "researched", "proposed", "critiqued", "checked", "approved"):
        state["steps"][s] = {"done": True, "timestamp": TS}
    state["steps"]["researched"]["sources"] = ["https://nist.gov/x"]
    save_state(tmp_path / SDIR / "auth.process.json", state)
    assert _run(tmp_path, monkeypatch, [f"{SDIR}/auth.md"]) == 1


def test_fails_on_out_of_order_timestamps(tmp_path, monkeypatch, capsys):
    _md(tmp_path)
    p = _present_ts(tmp_path)
    import json
    st = json.loads(p.read_text())
    st["steps"]["presented"]["timestamp"] = "2020-01-01T00:00:00Z"   # before earlier steps → back-dated
    p.write_text(json.dumps(st))
    assert _run(tmp_path, monkeypatch, [f"{SDIR}/auth.md"]) == 1
    assert "order" in capsys.readouterr().err.lower()
