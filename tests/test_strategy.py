"""Tests for emkeel strategy — scaffold + the anti-hallucination lint."""

from emkeel.strategy import _do_check, _do_new, lint_strategy, skeleton, slug

VALID = """# Strategy: auth
Status: APPROVED
## Goal
multi-tenant auth
## Context
- existing session in src/auth.py:10
## Options
| # | Option | Source | Pros | Cons | Risk |
|---|--------|--------|------|------|------|
| 1 | JWT+refresh | src/auth.py:10 | stateless | revocation | mid |
| 2 | server sessions | https://x.com/sessions | revoke easy | state | low |
## Recommendation
Option 1
## Non-goals
- no SSO
"""


def test_slug():
    assert slug("auth") == "auth"
    assert slug("Tech Stack!") == "tech-stack"


def test_skeleton_has_required_sections():
    s = skeleton("auth")
    for sec in ("## Goal", "## Context", "## Options", "## Recommendation"):
        assert sec in s


def test_lint_clean_doc_passes():
    assert lint_strategy(VALID) == []


def test_lint_flags_missing_section():
    doc = VALID.replace("## Recommendation\nOption 1\n", "")
    assert any("Recommendation" in p for p in lint_strategy(doc))


def test_lint_flags_too_few_options():
    assert any("at least 2" in p for p in lint_strategy(skeleton("auth")))   # skeleton has empty rows


def test_lint_flags_option_without_source():
    doc = VALID.replace("| 1 | JWT+refresh | src/auth.py:10 |", "| 1 | JWT+refresh |  |")
    assert any("no Source" in p for p in lint_strategy(doc))


def test_new_scaffolds_and_is_non_clobbering(tmp_path):
    assert _do_new("auth", tmp_path) == 0
    p = tmp_path / "emkeel-governance/strategy/auth.md"
    assert p.is_file() and "## Options" in p.read_text()
    p.write_text("custom")
    assert _do_new("auth", tmp_path) == 0          # exists → no clobber
    assert p.read_text() == "custom"


def test_check_fails_on_skeleton_passes_on_filled(tmp_path):
    _do_new("auth", tmp_path)                       # empty skeleton → check fails
    assert _do_check("auth", tmp_path) == 1
    (tmp_path / "emkeel-governance/strategy/auth.md").write_text(VALID)
    assert _do_check("auth", tmp_path) == 0         # filled + sourced → passes


def test_check_no_docs_ok(tmp_path):
    assert _do_check("", tmp_path) == 0             # nothing to check
