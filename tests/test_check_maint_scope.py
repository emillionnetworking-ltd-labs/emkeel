"""Tests for check_maint_scope — keeps the emkeel-maint lane honest."""

import emkeel.gates.check_maint_scope as m


def test_na_for_normal_branch(monkeypatch):
    monkeypatch.setenv("EMKEEL_BRANCH", "feat/ECO-9-x")
    assert m.main() == 0


def test_ok_when_only_managed(monkeypatch):
    monkeypatch.setenv("EMKEEL_BRANCH", "emkeel-maint/0.1.52-abc")
    monkeypatch.setenv("EMKEEL_BASE_REF", "main")
    monkeypatch.setattr(m, "changed_files", lambda base, run=m._run: ["AGENTS.md", "emkeel.toml"])
    assert m.main() == 0


def test_fails_on_stray_file(monkeypatch):
    monkeypatch.setenv("EMKEEL_BRANCH", "emkeel-maint/0.1.52-abc")
    monkeypatch.setenv("EMKEEL_BASE_REF", "main")
    monkeypatch.setattr(m, "changed_files", lambda base, run=m._run: ["AGENTS.md", "src/app.py"])
    assert m.main() == 1


def test_managed_paths_covers_wiring():
    mp = m.managed_paths()
    assert "AGENTS.md" in mp and "emkeel.toml" in mp and ".github/workflows/emkeel-ci.yml" in mp
