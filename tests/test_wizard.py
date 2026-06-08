"""Tests for the emkeel setup wizard (deterministic parts)."""

import subprocess

from emkeel.wizard import Answers, branch_name, derive_defaults, main, plan_lines, run_setup, t


def _git(args, cwd):
    subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True)


def _init_repo(p, remote="git@github.com:acme/web.git"):
    _git(["init", "-q"], p)
    _git(["config", "user.email", "t@t.co"], p)
    _git(["config", "user.name", "test"], p)
    _git(["config", "commit.gpgsign", "false"], p)
    if remote:
        _git(["remote", "add", "origin", remote], p)
    (p / "README.md").write_text("hi\n")
    _git(["add", "README.md"], p)
    _git(["commit", "-qm", "SCRUM-1: initial"], p)


def test_i18n_and_branch():
    assert t("existing", "es") == "Repo existente"
    assert t("existing", "en") == "Existing repo"
    assert t("existing", "xx") == "Existing repo"  # unknown lang → English fallback
    assert branch_name("SCRUM-9") == "chore/SCRUM-9-adopt-emkeel"


def test_derive_defaults(tmp_path):
    _init_repo(tmp_path)
    (tmp_path / "config.yml").write_text("jira: https://acme.atlassian.net\n")
    _git(["add", "config.yml"], tmp_path)
    _git(["commit", "-qm", "SCRUM-2: add config"], tmp_path)
    d = derive_defaults(tmp_path)
    assert d["github_repo"] == "acme/web"
    assert d["jira_project"] == "SCRUM"
    assert d["jira_url"] == "https://acme.atlassian.net"


def test_derive_defaults_outside_repo(tmp_path):
    # not a git repo → all empty, no crash
    assert derive_defaults(tmp_path) == {"github_repo": "", "jira_url": "", "jira_project": ""}


def test_plan_lines_existing_vs_new():
    a = Answers(lang="en", scenario="existing", jira_key="SCRUM-9999")
    assert any("chore/SCRUM-9999-adopt-emkeel" in ln for ln in plan_lines(a))
    b = Answers(lang="en", scenario="new")
    assert any("git init" in ln for ln in plan_lines(b))


def test_run_setup_existing(tmp_path):
    _init_repo(tmp_path)
    a = Answers(scenario="existing", mode="trial", github_repo="acme/web",
                jira_url="https://acme.atlassian.net", jira_project="SCRUM", jira_key="SCRUM-9999")
    run_setup(tmp_path, a)
    assert (tmp_path / "emkeel.toml").is_file() and (tmp_path / "AGENTS.md").is_file()
    cur = subprocess.run(["git", "branch", "--show-current"], cwd=tmp_path,
                         capture_output=True, text=True).stdout.strip()
    assert cur == "chore/SCRUM-9999-adopt-emkeel"
    st = subprocess.run(["git", "status", "--short"], cwd=tmp_path, capture_output=True, text=True).stdout
    assert "emkeel.toml" not in st  # committed, not left dangling


def test_run_setup_new(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_AUTHOR_NAME", "t"); monkeypatch.setenv("GIT_AUTHOR_EMAIL", "t@t.co")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "t"); monkeypatch.setenv("GIT_COMMITTER_EMAIL", "t@t.co")
    a = Answers(scenario="new", mode="real", github_repo="acme/new",
                jira_url="https://acme.atlassian.net", jira_project="ACME")
    run_setup(tmp_path, a)
    assert (tmp_path / ".git").exists() and (tmp_path / "emkeel.toml").is_file()


def test_main_smoke(tmp_path, monkeypatch, capsys):
    _init_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    # lang=en, scenario=existing, mode=trial, repo⏎, url⏎, proj⏎, key, continue=y
    answers = iter(["2", "1", "1", "", "", "", "SCRUM-9999", "y"])
    assert main(inp=lambda *_: next(answers)) == 0
    assert (tmp_path / "emkeel.toml").is_file()
    assert "Done" in capsys.readouterr().out
