"""Tests for the strategy-alignment gate: a feature serving a strategy must acknowledge how it aligns."""

import emkeel.gates.check_strategy_alignment as g

SPEC_ALIGNED = """# KEEL-3
Strategy: auth

## Alignment
- Implements decision D-002 (rotating refresh tokens) from the auth strategy.

## Acceptance Criteria
- works
"""

SPEC_NO_ALIGN = """# KEEL-3
Strategy: auth

## Acceptance Criteria
- works
"""

SPEC_EMPTY_ALIGN = """# KEEL-3
Strategy: auth

## Alignment

## Acceptance Criteria
- works
"""

SPEC_STANDALONE = """# KEEL-3
Strategy: none

## Acceptance Criteria
- works
"""


def _run(monkeypatch, tmp_path, branch, spec_text=None, has_strategy=True, key="KEEL-3"):
    specs = tmp_path / "specs"; specs.mkdir(exist_ok=True)
    strat = tmp_path / "strat"; strat.mkdir(exist_ok=True)
    if has_strategy:
        (strat / "auth.md").write_text("# Strategy: auth\n")
    if spec_text is not None:
        (specs / f"{key}.md").write_text(spec_text)
    monkeypatch.setenv("EMKEEL_BRANCH", branch)
    monkeypatch.setenv("EMKEEL_SPECS_DIR", str(specs))
    monkeypatch.setenv("EMKEEL_STRATEGY_DIR", str(strat))
    return g.main()


# ── AC1: Strategy: auth + no Alignment (strategy exists) → FAIL ────────────────

def test_missing_alignment_fails(monkeypatch, tmp_path):
    assert _run(monkeypatch, tmp_path, "feat/KEEL-3-x", SPEC_NO_ALIGN) == 1


# ── AC2: Strategy: auth + Alignment with content → PASS ────────────────────────

def test_alignment_with_content_passes(monkeypatch, tmp_path):
    assert _run(monkeypatch, tmp_path, "feat/KEEL-3-x", SPEC_ALIGNED) == 0


# ── AC3: empty Alignment heading → FAIL ────────────────────────────────────────

def test_empty_alignment_fails(monkeypatch, tmp_path):
    assert _run(monkeypatch, tmp_path, "feat/KEEL-3-x", SPEC_EMPTY_ALIGN) == 1


# ── AC4: Strategy: none → OK even without Alignment ────────────────────────────

def test_standalone_is_na(monkeypatch, tmp_path):
    assert _run(monkeypatch, tmp_path, "feat/KEEL-3-x", SPEC_STANDALONE) == 0


# ── AC5: no strategies in repo → dormant OK ────────────────────────────────────

def test_dormant_when_no_strategies(monkeypatch, tmp_path):
    assert _run(monkeypatch, tmp_path, "feat/KEEL-3-x", SPEC_NO_ALIGN, has_strategy=False) == 0


# ── AC6: non-feature branch → OK (N/A) ─────────────────────────────────────────

def test_non_feature_is_na(monkeypatch, tmp_path):
    assert _run(monkeypatch, tmp_path, "chore/KEEL-3-x", SPEC_NO_ALIGN) == 0
    assert _run(monkeypatch, tmp_path, "fix/KEEL-3-x", SPEC_NO_ALIGN) == 0


# ── deferral: missing spec / missing link / no key → OK (a sibling gate owns the FAIL) ─

def test_missing_spec_defers_to_plan_present(monkeypatch, tmp_path):
    assert _run(monkeypatch, tmp_path, "feat/KEEL-3-x", spec_text=None) == 0


def test_no_ticket_key_defers(monkeypatch, tmp_path):
    assert _run(monkeypatch, tmp_path, "feat/no-key-here", SPEC_NO_ALIGN) == 0


def test_missing_strategy_link_defers(monkeypatch, tmp_path):
    spec = "# KEEL-3\n\n## Acceptance Criteria\n- works\n"   # no `Strategy:` line
    assert _run(monkeypatch, tmp_path, "feat/KEEL-3-x", spec) == 0


# ── AC7: specs/strategy dirs injectable (a custom dir resolves the spec + strategy) ─

def test_dirs_injectable(monkeypatch, tmp_path):
    # the whole suite uses custom EMKEEL_SPECS_DIR/EMKEEL_STRATEGY_DIR; assert a positive resolves there.
    assert _run(monkeypatch, tmp_path, "feat/KEEL-3-x", SPEC_ALIGNED) == 0
    assert _run(monkeypatch, tmp_path, "feat/KEEL-3-x", SPEC_NO_ALIGN) == 1
