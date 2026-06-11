"""Tests for the strategy-link gate (anti strategy-drift). Born with its test."""

from emkeel.gates.check_strategy_link import main, strategy_link


def _setup(tmp_path, branch, spec_text=None, strategies=()):
    specs = tmp_path / "specs"; strat = tmp_path / "strategy"
    specs.mkdir(); strat.mkdir()
    for s in strategies:
        (strat / f"{s}.md").write_text(f"# Strategy: {s}\n")
    if spec_text is not None:
        (specs / "ECO-9.md").write_text(spec_text)
    return {"EMKEEL_BRANCH": branch, "EMKEEL_SPECS_DIR": str(specs), "EMKEEL_STRATEGY_DIR": str(strat)}


def _run(monkeypatch, env):
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    return main()


def test_non_feature_passes(tmp_path, monkeypatch):
    assert _run(monkeypatch, _setup(tmp_path, "chore/ECO-9-x", strategies=("auth",))) == 0


def test_dormant_when_no_strategies(tmp_path, monkeypatch):
    assert _run(monkeypatch, _setup(tmp_path, "feat/ECO-9-x", spec_text="# spec\n")) == 0


def test_missing_strategy_line_fails(tmp_path, monkeypatch):
    assert _run(monkeypatch, _setup(tmp_path, "feat/ECO-9-x", spec_text="# no link\n", strategies=("auth",))) == 1


def test_strategy_none_passes(tmp_path, monkeypatch):
    assert _run(monkeypatch, _setup(tmp_path, "feat/ECO-9-x", spec_text="Strategy: none\n", strategies=("auth",))) == 0


def test_valid_strategy_passes(tmp_path, monkeypatch):
    assert _run(monkeypatch, _setup(tmp_path, "feat/ECO-9-x", spec_text="Strategy: auth\n", strategies=("auth",))) == 0


def test_unknown_strategy_fails(tmp_path, monkeypatch):
    assert _run(monkeypatch, _setup(tmp_path, "feat/ECO-9-x", spec_text="Strategy: billing\n", strategies=("auth",))) == 1


def test_feature_without_spec_fails(tmp_path, monkeypatch):
    assert _run(monkeypatch, _setup(tmp_path, "feat/ECO-9-x", spec_text=None, strategies=("auth",))) == 1


def test_strategy_link_parse():
    assert strategy_link("foo\nStrategy: auth\nbar") == "auth"
    assert strategy_link("Strategy:none") == "none"
    assert strategy_link("no link here") is None
