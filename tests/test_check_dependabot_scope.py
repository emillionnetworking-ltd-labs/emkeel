"""Tests for check_dependabot_scope — keeps the dependabot lane honest (sibling of check_maint_scope)."""

import emkeel.gates.check_dependabot_scope as d


def test_na_for_normal_branch(monkeypatch):
    monkeypatch.setenv("EMKEEL_BRANCH", "feat/ECO-9-x")
    assert d.main() == 0


def test_na_for_maint_branch(monkeypatch):
    # the maint lane is governed by its OWN scope gate; this one is N/A for it.
    monkeypatch.setenv("EMKEEL_BRANCH", "emkeel-maint/0.1.71-abc")
    assert d.main() == 0


def test_ok_when_only_dependency_files(monkeypatch):
    monkeypatch.setenv("EMKEEL_BRANCH", "dependabot/npm_and_yarn/lodash-4.17.21")
    monkeypatch.setenv("EMKEEL_BASE_REF", "main")
    monkeypatch.setattr(d, "changed_files",
                        lambda base, run=None: ["package.json", "package-lock.json",
                                                ".github/workflows/ci.yml"])
    assert d.main() == 0


def test_fails_on_code_change(monkeypatch):
    # a dependabot branch must not smuggle real code past the ticket exemption.
    monkeypatch.setenv("EMKEEL_BRANCH", "dependabot/pip/requests-2.32.0")
    monkeypatch.setenv("EMKEEL_BASE_REF", "main")
    monkeypatch.setattr(d, "changed_files",
                        lambda base, run=None: ["requirements.txt", "src/app.py"])
    assert d.main() == 1


def test_is_dependency_path_accepts_manifests_and_actions():
    for p in ("package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
              "requirements.txt", "requirements-dev.txt", "poetry.lock", "pyproject.toml",
              "go.mod", "go.sum", "Cargo.toml", "Gemfile.lock", "composer.json",
              "api/MyApp.csproj", "sub/dir/package.json",
              ".github/workflows/ci.yml", ".github/dependabot.yml"):
        assert d.is_dependency_path(p) is True, p


def test_is_dependency_path_rejects_code_and_docs():
    for p in ("src/app.py", "README.md", "nexacore-api/src/main.ts", ".github/CODEOWNERS", ""):
        assert d.is_dependency_path(p) is False, p
