"""Tests for the review-assist helper. Born with main() coverage (KEEL-2 lesson)."""

from emkeel.review import extract_criteria, main, render_review_template

SPEC = """# T

## Acceptance Criteria
- first thing works
- second thing works

## Anti-regression
- x
"""


def test_extract_returns_items_in_order():
    assert extract_criteria(SPEC) == ["first thing works", "second thing works"]


def test_extract_empty_when_no_section():
    assert extract_criteria("# T\n\n## Plan\n- do x\n") == []


def test_extract_stops_at_next_heading():
    assert extract_criteria("## Acceptance Criteria\n- a\n## Next\n- b\n") == ["a"]


def test_template_lists_each_criterion():
    out = render_review_template("KEEL-4", ["a", "b"])
    assert "AC1: a" in out and "AC2: b" in out and "verdict:" in out


def test_template_handles_no_criteria():
    assert "No acceptance criteria" in render_review_template("KEEL-4", [])


def test_main_prints_template_when_spec_present(monkeypatch, tmp_path, capsys):
    (tmp_path / "KEEL-4.md").write_text(SPEC)
    monkeypatch.setenv("EMKEEL_SPECS_DIR", str(tmp_path))
    assert main(["KEEL-4"]) == 0
    assert "AC1: first thing works" in capsys.readouterr().out


def test_main_fails_when_spec_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("EMKEEL_SPECS_DIR", str(tmp_path))
    assert main(["KEEL-4"]) == 1


def test_main_usage_when_no_args(monkeypatch, tmp_path):
    monkeypatch.setenv("EMKEEL_SPECS_DIR", str(tmp_path))
    assert main([]) == 2
