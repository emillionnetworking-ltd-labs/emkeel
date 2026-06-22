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


def _drive_to_checked(tmp_path, topic="auth", *, sources=None, internal_only=False):
    """Drive the real engine to `checked`, recording provenance — the legitimate, complete path."""
    schema = strategy_process()
    p = tmp_path / SDIR / f"{topic}.process.json"
    advance_on_disk(schema, p, "scaffolded", {"topic": topic}, timestamp=TS)
    fields = {"internal_only": True} if internal_only else {"sources": sources or ["https://nist.gov/x"]}
    advance_on_disk(schema, p, "researched", fields, timestamp=TS)
    advance_on_disk(schema, p, "proposed", {"options": ["a", "b"]}, timestamp=TS)
    advance_on_disk(schema, p, "critiqued", {"critique": "adversarial pass done"}, timestamp=TS)
    advance_on_disk(schema, p, "checked", {"check_passed": True}, timestamp=TS)
    return p


def _run(tmp_path, monkeypatch, changed):
    monkeypatch.setattr(g, "changed_files", lambda base, **k: list(changed))
    monkeypatch.setenv("EMKEEL_BASE_REF", "main")
    monkeypatch.setenv("EMKEEL_REPO_DIR", str(tmp_path))
    monkeypatch.delenv("EMKEEL_STRATEGY_DIR", raising=False)
    return g.main()


# ── N/A + passing ──────────────────────────────────────────────────────────────

def test_na_when_no_strategy_doc_changed(tmp_path, monkeypatch):
    assert _run(tmp_path, monkeypatch, ["src/emkeel/cli.py", "README.md"]) == 0


def test_passes_with_process_at_checked_and_provenance(tmp_path, monkeypatch):
    _md(tmp_path)
    _drive_to_checked(tmp_path, sources=["https://pages.nist.gov/800-63b/", "src/auth/session.py:42"])
    assert _run(tmp_path, monkeypatch, [f"{SDIR}/auth.md"]) == 0


def test_passes_with_internal_only_provenance(tmp_path, monkeypatch):
    _md(tmp_path)
    _drive_to_checked(tmp_path, internal_only=True)            # no market dimension, declared explicitly
    assert _run(tmp_path, monkeypatch, [f"{SDIR}/auth.md"]) == 0


# ── failing cases ───────────────────────────────────────────────────────────────

def test_fails_when_process_json_missing(tmp_path, monkeypatch):
    _md(tmp_path)                                              # doc changed, but no .process.json committed
    assert _run(tmp_path, monkeypatch, [f"{SDIR}/auth.md"]) == 1


def test_fails_when_not_reached_checked(tmp_path, monkeypatch):
    _md(tmp_path)
    schema = strategy_process()
    p = tmp_path / SDIR / "auth.process.json"
    advance_on_disk(schema, p, "scaffolded", {"topic": "auth"}, timestamp=TS)
    advance_on_disk(schema, p, "researched", {"sources": ["https://nist.gov/x"]}, timestamp=TS)
    # stopped at researched → proposed/critiqued/checked not done
    assert _run(tmp_path, monkeypatch, [f"{SDIR}/auth.md"]) == 1


def test_fails_when_researched_lacks_provenance(tmp_path, monkeypatch):
    # a hand-forged state that reached 'checked' but whose researched step has NO real source.
    _md(tmp_path)
    p = tmp_path / SDIR / "auth.process.json"
    state = new_state(strategy_process())
    state["state"] = "checked"
    for s in ("scaffolded", "researched", "proposed", "critiqued", "checked"):
        state["steps"][s] = {"done": True, "timestamp": TS}
    state["steps"]["researched"]["sources"] = ["just some prose, not a real source"]
    save_state(p, state)
    assert _run(tmp_path, monkeypatch, [f"{SDIR}/auth.md"]) == 1


def test_fails_when_process_json_unparseable(tmp_path, monkeypatch):
    _md(tmp_path)
    (tmp_path / SDIR / "auth.process.json").write_text("{ not json")
    assert _run(tmp_path, monkeypatch, [f"{SDIR}/auth.md"]) == 1


def test_one_bad_doc_fails_the_build(tmp_path, monkeypatch):
    _md(tmp_path, "auth"); _drive_to_checked(tmp_path, "auth")     # auth is complete…
    _md(tmp_path, "cache")                                         # …cache has no process.json
    assert _run(tmp_path, monkeypatch, [f"{SDIR}/auth.md", f"{SDIR}/cache.md"]) == 1


def test_required_done_steps_is_through_checked():
    assert g.required_done_steps() == ["scaffolded", "researched", "proposed", "critiqued", "checked"]
