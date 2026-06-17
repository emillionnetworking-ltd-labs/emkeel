"""Tests for the acceptance-criteria gate. Born with main() coverage (KEEL-2 lesson)."""

from emkeel.gates.check_acceptance_criteria import has_acceptance_criteria, has_section, main

WITH = "# T\n\n## Acceptance Criteria\n- the thing works\n"
WITHOUT = "# T\n\n## Plan\n- do stuff\n"
EMPTY_SECTION = "# T\n\n## Acceptance Criteria\n\n## Anti-regression\n- x\n"


def test_has_section_generic():
    # the generalized helper backs has_acceptance_criteria; multi-word names match flexible whitespace.
    assert has_section("## Alignment\n- x\n", "alignment") is True
    assert has_section("## Alignment\n\n## Next\n", "alignment") is False     # empty section
    assert has_section("## Plan\n- x\n", "alignment") is False               # absent
    assert has_section("## Alignment", "alignment") is False                 # heading at EOF, no body
    assert has_section("###  acceptance   criteria \n- x\n", "acceptance criteria") is True


def test_detects_section_with_content():
    assert has_acceptance_criteria(WITH) is True


def test_missing_section():
    assert has_acceptance_criteria(WITHOUT) is False


def test_empty_section_is_not_enough():
    assert has_acceptance_criteria(EMPTY_SECTION) is False


def test_heading_is_case_insensitive():
    assert has_acceptance_criteria("## acceptance criteria\n- ok\n") is True


def _run_main(monkeypatch, tmp_path, branch, spec_text=None):
    if spec_text is not None:
        (tmp_path / "KEEL-3.md").write_text(spec_text)
    monkeypatch.setenv("EMKEEL_BRANCH", branch)
    monkeypatch.setenv("EMKEEL_SPECS_DIR", str(tmp_path))
    return main()


def test_main_passes_with_criteria(monkeypatch, tmp_path):
    assert _run_main(monkeypatch, tmp_path, "feat/KEEL-3-x", WITH) == 0


def test_main_fails_without_criteria(monkeypatch, tmp_path):
    assert _run_main(monkeypatch, tmp_path, "feat/KEEL-3-x", WITHOUT) == 1


def test_main_fails_when_spec_missing(monkeypatch, tmp_path):
    assert _run_main(monkeypatch, tmp_path, "feat/KEEL-3-x", None) == 1


def test_main_passes_for_non_feature(monkeypatch, tmp_path):
    assert _run_main(monkeypatch, tmp_path, "chore/KEEL-3-x", None) == 0
