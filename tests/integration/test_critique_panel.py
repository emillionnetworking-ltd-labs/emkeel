"""Integration: the critique panel enforced end to end — real engine + real gate, no mocks of the logic.

KEEL-118: `critiqued` must carry a multi-lens adversarial panel + a completeness critic; a non-trivial
strategy needs ≥3 distinct lenses (by the doc's `Impact:`). This drives the real engine to `validated` and
runs the real `check_strategy_process`: a 3-lens panel PASSES; a single lens on a high-impact doc FAILS.
"""

import emkeel.gates.check_strategy_process as gate
from emkeel.process import advance_on_disk
from emkeel.strategy import strategy_process

SDIR = "emkeel-governance/strategy"
TS = "2026-06-26T00:00:00Z"
KC = ["the pilot rejects it", "worse than the baseline"]
REALITY = {"case": "ECO-71", "method": "applied to one real case",
           "outcome": "pass", "evidence_ref": "https://example.com/pilot"}
PANEL = {"lens_discovery": "no sitemap; invisible to search", "lens_legal": "no cookie banner; GDPR risk",
         "lens_calibration": "thin vs the real render", "completeness": "no a11y lens — add it"}
ONE = {"lens_discovery": "no sitemap; invisible to search", "completeness": "none"}


def _drive(tmp_path, topic, critique, *, impact=None):
    d = tmp_path / SDIR
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{topic}.md").write_text(f"# Strategy: {topic}\n" + (f"Impact: {impact}\n" if impact else ""))
    s = strategy_process()
    p = d / f"{topic}.process.json"
    advance_on_disk(s, p, "scaffolded", {"topic": topic, "kill_criteria": KC}, timestamp=TS)
    advance_on_disk(s, p, "researched", {"internal_only": True}, timestamp=TS)
    advance_on_disk(s, p, "proposed", {"options": ["a", "b"]}, timestamp=TS)
    advance_on_disk(s, p, "critiqued", critique, timestamp=TS)
    advance_on_disk(s, p, "checked", {"check_passed": True}, timestamp=TS)
    advance_on_disk(s, p, "validated", REALITY, timestamp=TS)
    return p


def _run(tmp_path, monkeypatch, topic):
    monkeypatch.setattr(gate, "changed_files", lambda base, **k: [f"{SDIR}/{topic}.md"])
    monkeypatch.setattr(gate, "deleted_files", lambda base, **k: [])
    monkeypatch.setenv("EMKEEL_BASE_REF", "main")
    monkeypatch.setenv("EMKEEL_REPO_DIR", str(tmp_path))
    monkeypatch.delenv("EMKEEL_STRATEGY_DIR", raising=False)
    return gate.main()


def test_three_lens_panel_passes_end_to_end(tmp_path, monkeypatch):
    _drive(tmp_path, "auth", PANEL)
    assert _run(tmp_path, monkeypatch, "auth") == 0


def test_single_lens_high_impact_fails_end_to_end(tmp_path, monkeypatch, capsys):
    _drive(tmp_path, "auth", ONE)                            # no Impact declared → high → needs ≥3
    assert _run(tmp_path, monkeypatch, "auth") == 1
    assert "lens" in capsys.readouterr().err.lower()


def test_single_lens_low_impact_passes_end_to_end(tmp_path, monkeypatch):
    _drive(tmp_path, "trivial", ONE, impact="low")          # consciously trivial → 1 lens is enough
    assert _run(tmp_path, monkeypatch, "trivial") == 0
