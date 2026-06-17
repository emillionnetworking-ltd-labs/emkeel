"""Tests for the strategy-quality CI gate (now resolving Sources, not just non-emptiness)."""

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


def _repo_file(tmp_path, rel="src/x.py", lines=5):
    f = tmp_path / rel; f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("\n".join(str(i) for i in range(1, lines + 1)))


def test_dormant_when_no_strategies(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert g.main() == 0


def test_passes_on_grounded_strategy(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _repo_file(tmp_path)
    _strat(tmp_path, VALID)
    assert g.main() == 0


def test_fails_on_ungrounded_strategy(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _repo_file(tmp_path)
    _strat(tmp_path, VALID.replace("| 1 | a | src/x.py:1 |", "| 1 | a |  |"))   # option without a source
    assert g.main() == 1


def test_fails_when_repo_source_does_not_resolve(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)               # no src/x.py created → file:line can't resolve
    _strat(tmp_path, VALID)
    assert g.main() == 1


def test_repo_dir_is_injectable(tmp_path, monkeypatch):
    # gate resolves file:line against EMKEEL_REPO_DIR, not just cwd.
    monkeypatch.chdir(tmp_path)
    _repo_file(tmp_path)
    _strat(tmp_path, VALID)
    monkeypatch.setenv("EMKEEL_REPO_DIR", str(tmp_path))
    assert g.main() == 0
