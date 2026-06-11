"""Tests for `emkeel set` — change emkeel.toml values cleanly."""

from emkeel.init import Config, apply
from emkeel.setcfg import main


def test_set_changes_project(tmp_path, monkeypatch, capsys):
    apply(tmp_path, Config(jira_project="SCRUM", github_repo="o/r"), force=False, dry_run=False)
    monkeypatch.chdir(tmp_path)
    assert main(["jira-project", "ECO"]) == 0
    assert 'project_key = "ECO"' in (tmp_path / "emkeel.toml").read_text()
    assert "SCRUM" in capsys.readouterr().out  # reports the old→new change


def test_set_preserves_source(tmp_path, monkeypatch):
    src = "git+https://x/emkeel.git"
    apply(tmp_path, Config(jira_project="SCRUM", github_repo="o/r", emkeel_source=src), force=False, dry_run=False)
    monkeypatch.chdir(tmp_path)
    main(["jira-project", "ECO"])
    assert src in (tmp_path / "emkeel.toml").read_text()   # set must not clobber a custom source


def test_set_noop_when_same(tmp_path, monkeypatch, capsys):
    apply(tmp_path, Config(jira_project="ECO", github_repo="o/r"), force=False, dry_run=False)
    monkeypatch.chdir(tmp_path)
    assert main(["jira-project", "ECO"]) == 0
    assert "nothing to change" in capsys.readouterr().out


def test_set_rejects_unknown_field(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["bogus", "x"]) == 2
