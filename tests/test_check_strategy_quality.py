"""Tests for the strategy-quality CI gate."""

import emkeel.gates.check_strategy_quality as g

VALID = """# Strategy: auth
## Goal
g
## Context
- src/x.py:1
## Options
| # | Option | Source | Pros | Cons | Risk |
|---|---|---|---|---|---|
| 1 | a | src/x.py:1 | p | c | r |
| 2 | b | https://x.com | p | c | r |
## Recommendation
1
"""


def _strat(tmp_path, body):
    d = tmp_path / "emkeel-governance/strategy"; d.mkdir(parents=True, exist_ok=True)
    (d / "auth.md").write_text(body)


def test_dormant_when_no_strategies(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert g.main() == 0


def test_passes_on_grounded_strategy(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _strat(tmp_path, VALID)
    assert g.main() == 0


def test_fails_on_ungrounded_strategy(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _strat(tmp_path, VALID.replace("| 1 | a | src/x.py:1 |", "| 1 | a |  |"))   # option without a source
    assert g.main() == 1
