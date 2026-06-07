"""Tests del gate plan-presence. Dogfood: el gate nace con su test (test-on-fix)."""

from pathlib import Path

from emkeel.gates.check_plan_present import main, spec_path_for, spec_required


def test_feature_branch_requires_spec():
    assert spec_required("feat/KEEL-2-x") is True
    assert spec_required("feature/KEEL-9-y") is True


def test_non_feature_branch_does_not_require():
    assert spec_required("chore/KEEL-3-y") is False
    assert spec_required("fix/KEEL-4-z") is False
    assert spec_required("docs/KEEL-5-w") is False


def test_spec_path_uses_key():
    assert spec_path_for("KEEL-2", Path("emkeel-governance/specs")) == Path(
        "emkeel-governance/specs/KEEL-2.md"
    )


def test_present_spec_is_detected(tmp_path):
    (tmp_path / "KEEL-2.md").write_text("spec")
    assert spec_path_for("KEEL-2", tmp_path).is_file()


# --- main() end-to-end: el comportamiento real del gate (cierre del hueco de review KEEL-2) ---

def _run_main(monkeypatch, branch, specs_dir):
    monkeypatch.setenv("EMKEEL_BRANCH", branch)
    monkeypatch.setenv("EMKEEL_SPECS_DIR", str(specs_dir))
    return main()


def test_main_passes_when_feature_spec_present(monkeypatch, tmp_path):
    (tmp_path / "KEEL-2.md").write_text("spec")
    assert _run_main(monkeypatch, "feat/KEEL-2-x", tmp_path) == 0


def test_main_fails_when_feature_spec_missing(monkeypatch, tmp_path):
    assert _run_main(monkeypatch, "feat/KEEL-2-x", tmp_path) == 1


def test_main_passes_for_non_feature(monkeypatch, tmp_path):
    assert _run_main(monkeypatch, "chore/KEEL-3-y", tmp_path) == 0


def test_main_fails_for_feature_without_key(monkeypatch, tmp_path):
    assert _run_main(monkeypatch, "feat/no-ticket", tmp_path) == 1
