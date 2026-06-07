"""Tests for emkeel uninstall (reverse init)."""

from emkeel.init import Config, apply
from emkeel.uninstall import apply_uninstall, main

CFG = Config(jira_url="https://x.atlassian.net", jira_project="DEMO", github_repo="o/r")


def _governed(tmp_path):
    apply(tmp_path, CFG, force=False, dry_run=False)
    return tmp_path


def test_uninstall_removes_wiring_keeps_governance(tmp_path):
    _governed(tmp_path)
    apply_uninstall(tmp_path, purge=False, dry_run=False)
    assert not (tmp_path / "emkeel.toml").exists()
    assert not (tmp_path / ".github/workflows/emkeel-ci.yml").exists()
    assert not (tmp_path / "AGENTS.md").exists()
    assert not (tmp_path / "CLAUDE.md").exists()
    assert (tmp_path / "emkeel-governance").is_dir()  # history kept
    # emkeel created both here (fresh tmp → each holds only emkeel's line) → removed entirely
    assert not (tmp_path / ".gitattributes").exists()
    assert not (tmp_path / ".gitignore").exists()


def test_uninstall_preserves_user_gitignore(tmp_path):
    # The user already had a .gitignore (with their own .env) before Emkeel.
    (tmp_path / ".gitignore").write_text("node_modules/\n.env\ndist/\n")
    apply(tmp_path, CFG, force=False, dry_run=False)        # init: .env present → append-skip
    apply_uninstall(tmp_path, purge=False, dry_run=False)
    gi = (tmp_path / ".gitignore").read_text()
    assert "node_modules/" in gi and ".env" in gi and "dist/" in gi  # untouched, not stripped


def test_purge_also_removes_governance(tmp_path):
    _governed(tmp_path)
    apply_uninstall(tmp_path, purge=True, dry_run=False)
    assert not (tmp_path / "emkeel-governance").exists()


def test_dry_run_changes_nothing(tmp_path):
    _governed(tmp_path)
    apply_uninstall(tmp_path, purge=True, dry_run=True)
    assert (tmp_path / "emkeel.toml").exists()
    assert (tmp_path / "emkeel-governance").is_dir()


def test_cli_default_is_dry_run(tmp_path, capsys):
    _governed(tmp_path)
    assert main([str(tmp_path)]) == 0
    assert (tmp_path / "emkeel.toml").exists()  # nothing removed without --yes
    assert "dry-run" in capsys.readouterr().out
