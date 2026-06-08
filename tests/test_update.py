"""Tests for emkeel update (refresh wiring to the installed version)."""

from emkeel.init import Config, apply
from emkeel.update import load_cfg, main

CFG = Config(jira_url="https://x.atlassian.net", jira_project="DEMO", github_repo="o/r")


def test_load_cfg_reads_emkeel_toml(tmp_path):
    apply(tmp_path, CFG, force=False, dry_run=False)        # writes emkeel.toml
    cfg = load_cfg(tmp_path)
    assert cfg.github_repo == "o/r" and cfg.jira_project == "DEMO"
    assert cfg.jira_url == "https://x.atlassian.net"


def test_load_cfg_missing(tmp_path):
    assert load_cfg(tmp_path) is None


def test_update_refreshes_stale_wiring(tmp_path, monkeypatch):
    apply(tmp_path, CFG, force=False, dry_run=False)
    # simulate an OLD AGENTS.md (adopted on an earlier version, no onboard rule)
    (tmp_path / "AGENTS.md").write_text("# old contract\nno rule here\n")
    (tmp_path / "emkeel-governance" / "specs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "emkeel-governance" / "specs" / "MINE.md").write_text("my spec")
    monkeypatch.chdir(tmp_path)
    assert main([]) == 0
    agents = (tmp_path / "AGENTS.md").read_text()
    assert "emkeel onboard" in agents                       # refreshed to the current template
    assert (tmp_path / "emkeel-governance" / "specs" / "MINE.md").read_text() == "my spec"  # artifacts untouched


def test_update_without_toml(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main([]) == 1
    assert "emkeel setup" in capsys.readouterr().out
