"""Tests for check_critical_integration — a critical-surface change must ship an integration test."""

import emkeel.gates.check_critical_integration as g


def _run(monkeypatch, changed):
    monkeypatch.setattr(g, "changed_files", lambda base, **k: list(changed))
    monkeypatch.setenv("EMKEEL_BASE_REF", "main")
    return g.main()


# ── the manifest is explicit + correct ──────────────────────────────────────────

def test_manifest_marks_the_critical_surfaces():
    for f in ("src/emkeel/jira.py", "src/emkeel/isolation.py", "src/emkeel/init.py",
              "src/emkeel/update.py", "src/emkeel/ship.py", "src/emkeel/process.py",
              "src/emkeel/strategy.py",
              "src/emkeel/gates/check_ticket_link.py"):          # any gate, via the dir prefix
        assert g.is_critical(f), f


def test_manifest_ignores_non_critical():
    for f in ("src/emkeel/review.py", "src/emkeel/version.py", "README.md",
              "tests/test_jira.py", "emkeel-governance/specs/KEEL-1.md"):
        assert g.is_critical(f) is False, f


def test_is_integration_test():
    assert g.is_integration_test("tests/integration/test_x.py") is True
    assert g.is_integration_test("tests/test_x.py") is False


# ── the rule (deterministic, diff-based) ────────────────────────────────────────

def test_na_when_no_critical_surface(monkeypatch):
    assert _run(monkeypatch, ["src/emkeel/review.py", "README.md", "tests/test_review.py"]) == 0


def test_fails_critical_change_without_integration_test(monkeypatch, capsys):
    # the KEEL-93/94 shape: a critical surface changed, only a unit test added → FAIL.
    rc = _run(monkeypatch, ["src/emkeel/jira.py", "tests/test_jira.py"])
    assert rc == 1
    assert "integration test" in capsys.readouterr().err


def test_passes_critical_change_with_integration_test(monkeypatch):
    assert _run(monkeypatch, ["src/emkeel/jira.py", "tests/integration/test_creds_to_jira_create.py"]) == 0


def test_gate_file_itself_is_critical(monkeypatch):
    # changing the enforcement layer requires an integration test too.
    assert _run(monkeypatch, ["src/emkeel/gates/check_critical_integration.py"]) == 1
    assert _run(monkeypatch, ["src/emkeel/gates/check_critical_integration.py",
                              "tests/integration/test_x.py"]) == 0
