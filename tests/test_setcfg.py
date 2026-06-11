"""Tests for `emkeel set` — change emkeel.toml values cleanly."""

from emkeel.init import Config, apply
from emkeel.setcfg import main


def test_set_changes_project(tmp_path, monkeypatch, capsys):
    apply(tmp_path, Config(jira_project="SCRUM", github_repo="o/r"), force=False, dry_run=False)
    monkeypatch.chdir(tmp_path)
    assert main(["jira-project", "ECO", "--no-ship"]) == 0
    assert 'project_key = "ECO"' in (tmp_path / "emkeel.toml").read_text()
    assert "SCRUM" in capsys.readouterr().out  # reports the old→new change


def test_set_preserves_source(tmp_path, monkeypatch):
    src = "git+https://x/emkeel.git"
    apply(tmp_path, Config(jira_project="SCRUM", github_repo="o/r", emkeel_source=src), force=False, dry_run=False)
    monkeypatch.chdir(tmp_path)
    main(["jira-project", "ECO", "--no-ship"])
    assert src in (tmp_path / "emkeel.toml").read_text()   # set must not clobber a custom source


def test_set_noop_when_same(tmp_path, monkeypatch, capsys):
    apply(tmp_path, Config(jira_project="ECO", github_repo="o/r"), force=False, dry_run=False)
    monkeypatch.chdir(tmp_path)
    assert main(["jira-project", "ECO"]) == 0
    assert "nothing to change" in capsys.readouterr().out


def test_set_rejects_unknown_field(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["bogus", "x"]) == 2


def test_set_ships_by_default(tmp_path, monkeypatch):
    apply(tmp_path, Config(jira_project="SCRUM", github_repo="o/r"), force=False, dry_run=False)
    monkeypatch.chdir(tmp_path)
    calls = []
    import emkeel.ship as shipmod
    monkeypatch.setattr(shipmod, "ship_set", lambda attr, value, target=None: calls.append((attr, value)) or 0)
    assert main(["jira-project", "ECO"]) == 0
    assert calls and calls[0] == ("jira_project", "ECO")


def test_set_no_ship(tmp_path, monkeypatch):
    apply(tmp_path, Config(jira_project="SCRUM", github_repo="o/r"), force=False, dry_run=False)
    monkeypatch.chdir(tmp_path)
    calls = []
    import emkeel.ship as shipmod
    monkeypatch.setattr(shipmod, "ship_set", lambda attr, value, target=None: calls.append(1) or 0)
    assert main(["jira-project", "ECO", "--no-ship"]) == 0
    assert calls == []
    assert 'project_key = "ECO"' in (tmp_path / "emkeel.toml").read_text()
