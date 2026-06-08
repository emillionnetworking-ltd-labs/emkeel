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
