"""Tests for emkeel strategy — scaffold + the anti-hallucination lint (now with Source RESOLUTION)."""

from emkeel.strategy import (
    _do_check,
    _do_new,
    _repo_problem,
    _url_problem,
    classify_source,
    lint_strategy,
    review_strategy,
    skeleton,
    slug,
)

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


def _repo(tmp_path, rel="src/auth.py", lines=20):
    """Materialise a repo file the VALID fixture's file:line sources resolve against."""
    f = tmp_path / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("\n".join(f"line {i}" for i in range(1, lines + 1)))
    return f


def test_slug():
    assert slug("auth") == "auth"
    assert slug("Tech Stack!") == "tech-stack"


def test_skeleton_has_required_sections():
    s = skeleton("auth")
    for sec in ("## Goal", "## Context", "## Options", "## Recommendation"):
        assert sec in s


def test_lint_clean_doc_passes():
    # pure-text lint (no repo_root): repo paths are skipped, not resolved.
    assert lint_strategy(VALID) == []


def test_lint_flags_missing_section():
    doc = VALID.replace("## Recommendation\nOption 1\n", "")
    assert any("Recommendation" in p for p in lint_strategy(doc))


def test_lint_flags_too_few_options():
    assert any("at least 2" in p for p in lint_strategy(skeleton("auth")))   # skeleton has empty rows


def test_lint_flags_option_without_source():
    doc = VALID.replace("| 1 | JWT+refresh | src/auth.py:10 |", "| 1 | JWT+refresh |  |")
    assert any("no Source" in p for p in lint_strategy(doc))


# ── source classification ──────────────────────────────────────────────────────

def test_classify_source():
    assert classify_source("src/auth.py:10") == "repo"
    assert classify_source("src/auth.py:10-20") == "repo"
    assert classify_source("src/auth.py") == "repo"                  # clean path with '/' → repo (existence)
    assert classify_source("https://example.com/x") == "url"
    assert classify_source("https//typo-no-colon") == "url"          # url *intent* → judged malformed later
    assert classify_source("AUTH-v2.md §5 D-002") == "external"      # prose/spaces → not a clean path
    assert classify_source("auth.py") == "external"                  # bare filename, no '/' → external
    assert classify_source("auth.py:10") == "external"               # bare filename + line, no '/' → external


# ── AC2: URL well-formedness, offline ──────────────────────────────────────────

def test_url_problem_offline():
    assert _url_problem("https://pages.nist.gov/800-63-3/") is None
    assert _url_problem("https//missing-colon") is not None
    assert _url_problem("http://") is not None


# ── AC1: file:line resolution ──────────────────────────────────────────────────

def test_repo_problem_resolves(tmp_path):
    _repo(tmp_path, "src/auth.py", 20)
    assert _repo_problem("src/auth.py:10", tmp_path) is None
    assert _repo_problem("src/auth.py:5-15", tmp_path) is None


def test_repo_problem_missing_file(tmp_path):
    assert "not found" in _repo_problem("src/nope.py:1", tmp_path)


def test_repo_problem_line_out_of_range(tmp_path):
    _repo(tmp_path, "src/auth.py", 20)
    assert "out of range" in _repo_problem("src/auth.py:99", tmp_path)
    assert "out of range" in _repo_problem("src/auth.py:10-99", tmp_path)
    assert "out of range" in _repo_problem("src/auth.py:15-5", tmp_path)   # b < a


# ── path-only repo source (no line) → existence-only resolution ────────────────

def test_repo_path_no_line_existing_passes(tmp_path):
    _repo(tmp_path, "src/auth.py", 20)
    assert _repo_problem("src/auth.py", tmp_path) is None             # exists → PASS (no line needed)


def test_repo_path_no_line_missing_fails(tmp_path):
    # an invented path can't dodge resolution by omitting the line.
    assert "not found" in _repo_problem("src/nope.py", tmp_path)


def test_review_repo_path_no_line_missing_fails(tmp_path):
    _repo(tmp_path, "src/auth.py", 20)
    doc = VALID.replace("| 2 | server sessions | https://x.com/sessions |",
                        "| 2 | server sessions | src/nope.py |")
    fails, _warns, _u = review_strategy(doc, tmp_path)
    assert any("not found" in f for f in fails)


# ── AC3: external → WARN, counted ──────────────────────────────────────────────

def test_review_external_is_warn_not_fail(tmp_path):
    _repo(tmp_path, "src/auth.py", 20)
    doc = VALID.replace("| 2 | server sessions | https://x.com/sessions |",
                        "| 2 | server sessions | AUTH-v2.md §5 D-002 |")
    fails, warns, unverifiable = review_strategy(doc, tmp_path)
    assert fails == []
    assert unverifiable == 1
    assert any("unverifiable" in w for w in warns)


def test_review_malformed_url_fails(tmp_path):
    _repo(tmp_path, "src/auth.py", 20)
    doc = VALID.replace("https://x.com/sessions", "https//x.com/sessions")
    fails, _warns, _u = review_strategy(doc, tmp_path)
    assert any("malformed URL" in f for f in fails)


# ── scaffold + check (end to end) ──────────────────────────────────────────────

def test_new_scaffolds_and_is_non_clobbering(tmp_path):
    assert _do_new("auth", tmp_path) == 0
    p = tmp_path / "emkeel-governance/strategy/auth.md"
    assert p.is_file() and "## Options" in p.read_text()
    p.write_text("custom")
    assert _do_new("auth", tmp_path) == 0          # exists → no clobber
    assert p.read_text() == "custom"


def test_check_fails_on_skeleton_passes_on_filled(tmp_path):
    _repo(tmp_path, "src/auth.py", 20)
    _do_new("auth", tmp_path)                       # empty skeleton → check fails
    assert _do_check("auth", tmp_path) == 1
    (tmp_path / "emkeel-governance/strategy/auth.md").write_text(VALID)
    assert _do_check("auth", tmp_path) == 0         # filled + every source RESOLVES → passes


def test_check_fails_when_repo_source_unresolvable(tmp_path):
    # no src/auth.py created → the file:line source can't resolve → FAIL.
    (tmp_path / "emkeel-governance/strategy").mkdir(parents=True)
    (tmp_path / "emkeel-governance/strategy/auth.md").write_text(VALID)
    assert _do_check("auth", tmp_path) == 1


def test_check_no_docs_ok(tmp_path):
    assert _do_check("", tmp_path) == 0             # nothing to check
