"""Tests del gate plan-presence. Dogfood: el gate nace con su test (test-on-fix)."""

from emkeel.gates.check_plan_present import spec_path_for, spec_required


def test_feature_branch_requires_spec():
    assert spec_required("feat/KEEL-2-x") is True
    assert spec_required("feature/KEEL-9-y") is True


def test_non_feature_branch_does_not_require():
    assert spec_required("chore/KEEL-3-y") is False
    assert spec_required("fix/KEEL-4-z") is False
    assert spec_required("docs/KEEL-5-w") is False


def test_spec_path_uses_key():
    from pathlib import Path

    assert spec_path_for("KEEL-2", Path("emkeel-governance/specs")) == Path(
        "emkeel-governance/specs/KEEL-2.md"
    )


def test_present_spec_is_detected(tmp_path):
    (tmp_path / "KEEL-2.md").write_text("spec")
    assert spec_path_for("KEEL-2", tmp_path).is_file()
