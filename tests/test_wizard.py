"""Tests for the emkeel setup wizard (deterministic parts)."""

import subprocess

import pytest

from emkeel.wizard import (
    Answers, _choice, branch_name, derive_defaults, is_existing_repo, main, next_steps,
    plan_lines, run_setup, t,
)


@pytest.fixture(autouse=True)
def _no_connect_offer(monkeypatch):
    # These tests isolate `setup`; the end-of-wizard connect offer is tested separately.
    monkeypatch.setattr("emkeel.connect.gh_ok", lambda *a, **k: False)


def _git(args, cwd):
    subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True)


def _init_repo(p, remote="git@github.com:acme/web.git"):
    _git(["init", "-q"], p)
    _git(["symbolic-ref", "HEAD", "refs/heads/main"], p)  # deterministic default branch (CI may default to master)
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


def test_choice_default_and_cancel():
    opts = [("a", "A"), ("b", "B")]
    assert _choice("p", opts, inp=lambda *_: "") == "a"      # Enter → first/default
    assert _choice("p", opts, inp=lambda *_: "2") == "b"     # numbered
    assert _choice("p", opts, inp=lambda *_: "c") is None    # cancel
    assert _choice("p", opts, inp=lambda *_: "cancelar") is None


def test_derive_defaults(tmp_path):
    _init_repo(tmp_path)
    (tmp_path / "config.yml").write_text("jira: https://acme.atlassian.net\n")
    _git(["add", "config.yml"], tmp_path)
    _git(["commit", "-qm", "SCRUM-2: add config"], tmp_path)
    d = derive_defaults(tmp_path)
    assert d == {"github_repo": "acme/web", "jira_project": "SCRUM", "jira_url": "https://acme.atlassian.net"}


def test_derive_defaults_outside_repo(tmp_path):
    assert derive_defaults(tmp_path) == {"github_repo": "", "jira_url": "", "jira_project": ""}


def test_plan_and_next_steps():
    a = Answers(lang="en", scenario="existing", jira_key="SCRUM-9", jira_url="https://x", jira_project="SCRUM")
    assert any("chore/SCRUM-9-adopt-emkeel" in ln for ln in plan_lines(a))
    ns = next_steps(a)
    assert "push" in ns.lower() and "emkeel eject" in ns          # real next steps, no trial


def test_run_setup_existing(tmp_path):
    _init_repo(tmp_path)
    a = Answers(scenario="existing", github_repo="acme/web",
                jira_url="https://acme.atlassian.net", jira_project="SCRUM", jira_key="SCRUM-9999")
    run_setup(tmp_path, a)
    assert (tmp_path / "emkeel.toml").is_file() and (tmp_path / "AGENTS.md").is_file()
    cur = subprocess.run(["git", "branch", "--show-current"], cwd=tmp_path,
                         capture_output=True, text=True).stdout.strip()
    assert cur == "chore/SCRUM-9999-adopt-emkeel"


def test_run_setup_new(tmp_path, monkeypatch):
    for k in ("NAME", "EMAIL"):
        monkeypatch.setenv(f"GIT_AUTHOR_{k}", "t"); monkeypatch.setenv(f"GIT_COMMITTER_{k}", "t")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "t@t.co"); monkeypatch.setenv("GIT_COMMITTER_EMAIL", "t@t.co")
    a = Answers(scenario="new", github_repo="acme/new", jira_url="https://x", jira_project="ACME")
    run_setup(tmp_path, a)
    assert (tmp_path / ".git").exists() and (tmp_path / "emkeel.toml").is_file()


def test_main_smoke(tmp_path, monkeypatch, capsys):
    _init_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    # lang=en, scenario=existing, repo⏎, url⏎, proj⏎, key, continue=y  (no trial question)
    answers = iter(["2", "1", "", "", "", "SCRUM-9999", "y"])
    assert main(inp=lambda *_: next(answers)) == 0
    assert (tmp_path / "emkeel.toml").is_file()
    assert "Done" in capsys.readouterr().out


def test_main_cancel(tmp_path, monkeypatch, capsys):
    _init_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert main(inp=lambda *_: "c") == 0          # cancel at the first menu
    assert not (tmp_path / "emkeel.toml").exists()  # nothing done
    assert "ancel" in capsys.readouterr().out


def test_is_existing_repo(tmp_path):
    assert is_existing_repo(tmp_path) is False        # empty dir, no commits
    _init_repo(tmp_path)
    assert is_existing_repo(tmp_path) is True          # has a commit


def _branch(p):
    return subprocess.run(["git", "branch", "--show-current"], cwd=p,
                          capture_output=True, text=True).stdout.strip()


def test_main_new_in_existing_repo_asks_and_recommends_existing(tmp_path, monkeypatch, capsys):
    # The footgun: a real repo, but the user answers "new project".
    _init_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    # lang=en, scenario=NEW(2) → wizard asks → pick existing(1) → repo⏎,url⏎,proj⏎,key,continue
    answers = iter(["2", "2", "1", "", "", "", "SCRUM-7", "y"])
    assert main(inp=lambda *_: next(answers)) == 0
    out = capsys.readouterr().out
    assert "already a git repo with history" in out      # informed, not silent
    assert _branch(tmp_path) == "chore/SCRUM-7-adopt-emkeel"   # branch, NOT main
    assert subprocess.run(["git", "show", "main:emkeel.toml"], cwd=tmp_path,
                          capture_output=True).returncode != 0  # main untouched


def test_main_new_in_existing_repo_user_insists_new(tmp_path, monkeypatch, capsys):
    # If the user explicitly picks "new" anyway, it's allowed (their informed choice).
    _init_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    # lang=en, scenario=NEW(2) → wizard asks → pick new(2) → repo⏎,url⏎,proj⏎,continue
    answers = iter(["2", "2", "2", "", "", "", "y"])
    assert main(inp=lambda *_: next(answers)) == 0
    assert _branch(tmp_path) == "main"                   # stayed on main (their choice)
    assert (tmp_path / "emkeel.toml").is_file()


def test_main_detects_existing(tmp_path, monkeypatch, capsys):
    (tmp_path / "emkeel.toml").write_text("[jira]\n")  # already set up
    monkeypatch.chdir(tmp_path)
    # should refuse without asking anything; inp would raise if called
    def _boom(*_):
        raise AssertionError("should not prompt when already set up")
    assert main(inp=_boom) == 0
    assert "already set up" in capsys.readouterr().out


def test_main_existing_no_repo_asks_then_creates(tmp_path, monkeypatch, capsys):
    # "existing" answered but there's no repo → wizard asks; user creates new here.
    monkeypatch.chdir(tmp_path)
    for k in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{k}_NAME", "t"); monkeypatch.setenv(f"GIT_{k}_EMAIL", "t@t.co")
    answers = iter(["2", "1", "1", "", "", "", "y"])   # en, existing, create-new, fields⏎, continue
    assert main(inp=lambda *_: next(answers)) == 0
    assert "right folder" in capsys.readouterr().out            # informed
    assert (tmp_path / ".git").exists() and (tmp_path / "emkeel.toml").is_file()


def test_main_existing_no_repo_cancel(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    answers = iter(["2", "1", "c"])                    # en, existing, then cancel
    assert main(inp=lambda *_: next(answers)) == 0
    assert not (tmp_path / ".git").exists() and not (tmp_path / "emkeel.toml").exists()


def test_next_steps_new_project_creates_repo():
    a = Answers(lang="en", scenario="new", github_repo="acme/demo",
                jira_url="https://x", jira_project="ACME")
    ns = next_steps(a)
    assert "gh repo create acme/demo" in ns and "--push" in ns   # new project: create+push first


def test_main_offers_connect_when_gh_available(tmp_path, monkeypatch, capsys):
    # When gh is authed, finishing setup offers to connect (and runs it if accepted).
    _init_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("emkeel.connect.gh_ok", lambda *a, **k: True)
    called = {}
    monkeypatch.setattr("emkeel.connect.main", lambda argv=None, **kw: called.setdefault("yes", True) or 0)
    # lang=en, existing, repo⏎,url⏎,proj⏎, key, continue=y, connect-offer=y
    answers = iter(["2", "1", "", "", "", "SCRUM-9999", "y", "y"])
    assert main(inp=lambda *_: next(answers)) == 0
    assert called.get("yes") is True            # connect was invoked from the wizard


def test_main_connect_offer_declined(tmp_path, monkeypatch):
    _init_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("emkeel.connect.gh_ok", lambda *a, **k: True)
    called = {}
    monkeypatch.setattr("emkeel.connect.main", lambda argv=None, **kw: called.setdefault("yes", True) or 0)
    answers = iter(["2", "1", "", "", "", "SCRUM-9999", "y", "n"])   # decline connect
    assert main(inp=lambda *_: next(answers)) == 0
    assert "yes" not in called                   # connect NOT invoked
