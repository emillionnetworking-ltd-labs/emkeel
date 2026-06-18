"""Tests del primer gate. Dogfooding: el gate nace con su test (test-on-fix desde día 1)."""

from emkeel.gates.check_ticket_link import find_ticket_key


def test_finds_key_in_branch():
    assert find_ticket_key("feature/KEEL-12-add-gate", "") == "KEEL-12"


def test_finds_key_in_pr_title():
    assert find_ticket_key("", "PROD-345: fix login") == "PROD-345"


def test_branch_takes_precedence_when_both_present():
    assert find_ticket_key("feature/KEEL-1-x", "KEEL-2: y") == "KEEL-1"


def test_returns_none_when_no_key():
    assert find_ticket_key("feature/no-ticket", "just a title") is None


def test_gate_warns_on_stale_wiring(tmp_path, monkeypatch, capsys):
    from emkeel.init import Config, apply
    from emkeel.gates.check_ticket_link import _warn_if_stale_wiring
    apply(tmp_path, Config(github_repo="o/r"), force=False, dry_run=False)
    (tmp_path / "AGENTS.md").write_text("old")          # force drift
    monkeypatch.chdir(tmp_path)
    _warn_if_stale_wiring()
    out = capsys.readouterr().out
    assert "::warning::" in out and "emkeel update" in out


def test_gate_silent_when_wiring_current(tmp_path, monkeypatch, capsys):
    from emkeel.init import Config, apply
    from emkeel.gates.check_ticket_link import _warn_if_stale_wiring
    apply(tmp_path, Config(github_repo="o/r"), force=False, dry_run=False)
    monkeypatch.chdir(tmp_path)
    _warn_if_stale_wiring()
    assert "::warning::" not in capsys.readouterr().out


def test_gate_warns_on_project_mismatch(tmp_path, monkeypatch, capsys):
    from emkeel.init import Config, apply
    from emkeel.gates.check_ticket_link import _warn_if_project_mismatch
    apply(tmp_path, Config(jira_project="SCRUM", github_repo="o/r"), force=False, dry_run=False)
    monkeypatch.chdir(tmp_path)
    _warn_if_project_mismatch("ECO-1")
    out = capsys.readouterr().out
    assert "::warning::" in out and "SCRUM" in out and "ECO-1" in out


def test_gate_silent_when_project_matches(tmp_path, monkeypatch, capsys):
    from emkeel.init import Config, apply
    from emkeel.gates.check_ticket_link import _warn_if_project_mismatch
    apply(tmp_path, Config(jira_project="SCRUM", github_repo="o/r"), force=False, dry_run=False)
    monkeypatch.chdir(tmp_path)
    _warn_if_project_mismatch("SCRUM-9")
    assert "::warning::" not in capsys.readouterr().out


def test_ticket_link_accepts_maint_branch(monkeypatch, capsys):
    from emkeel.gates.check_ticket_link import main
    monkeypatch.setenv("EMKEEL_BRANCH", "emkeel-maint/0.1.52-abc")
    monkeypatch.delenv("EMKEEL_PR_TITLE", raising=False)
    assert main() == 0                                   # no Jira ticket required for the lane
    assert "maintenance" in capsys.readouterr().out.lower()


# ── existence verification (KEEL-83): gate now checks the ticket EXISTS in Jira ─────────

import emkeel.jira as J
from emkeel.gates.check_ticket_link import main


def _no_secrets(monkeypatch):
    for k in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_TOKEN"):
        monkeypatch.delenv(k, raising=False)


def _with_secrets(monkeypatch):
    for k in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_TOKEN"):
        monkeypatch.setenv(k, "x")


def test_no_key_still_fails(monkeypatch):
    _no_secrets(monkeypatch)
    monkeypatch.setenv("EMKEEL_BRANCH", "feat/no-ticket-here")
    monkeypatch.delenv("EMKEEL_PR_TITLE", raising=False)
    assert main() == 1


def test_secrets_absent_is_syntax_only_warning(monkeypatch, capsys):
    _no_secrets(monkeypatch)
    monkeypatch.setenv("EMKEEL_BRANCH", "feat/KEEL-78-x")
    monkeypatch.delenv("EMKEEL_PR_TITLE", raising=False)
    assert main() == 0                                   # degrades, non-blocking
    out = capsys.readouterr().out
    assert "::warning::" in out and "existence" in out.lower()


def test_secrets_present_and_ticket_exists_passes(monkeypatch, capsys):
    _with_secrets(monkeypatch)
    monkeypatch.setenv("EMKEEL_BRANCH", "feat/KEEL-78-x")
    monkeypatch.setattr(J, "issue_status", lambda key: 200)
    assert main() == 0
    assert "exists in Jira" in capsys.readouterr().out


def test_secrets_present_and_ticket_missing_hard_fails(monkeypatch, capsys):
    _with_secrets(monkeypatch)
    monkeypatch.setenv("EMKEEL_BRANCH", "feat/KEEL-9999-ghost")
    monkeypatch.setattr(J, "issue_status", lambda key: 404)
    assert main() == 1                                   # the hard line
    assert "::error::" in capsys.readouterr().err


def test_inconclusive_jira_error_does_not_block(monkeypatch, capsys):
    _with_secrets(monkeypatch)
    monkeypatch.setenv("EMKEEL_BRANCH", "feat/KEEL-78-x")
    monkeypatch.setattr(J, "issue_status", lambda key: 500)
    assert main() == 0                                   # don't block a merge on a Jira hiccup
    assert "::warning::" in capsys.readouterr().out


def test_maint_branch_skips_existence_check(monkeypatch):
    _with_secrets(monkeypatch)                           # even with secrets, the lane is exempt
    monkeypatch.setenv("EMKEEL_BRANCH", "emkeel-maint/0.1.70-abc")
    monkeypatch.delenv("EMKEEL_PR_TITLE", raising=False)
    called = {"n": 0}
    monkeypatch.setattr(J, "issue_status", lambda key: called.update(n=called["n"] + 1) or 404)
    assert main() == 0 and called["n"] == 0             # never queried Jira
