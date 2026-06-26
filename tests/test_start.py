"""emkeel start — ticket FIRST, then a branch named from the new key (the correct order, made easy)."""

import subprocess

import emkeel.jira as jira
import emkeel.start as start


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


def _repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q"); _git(repo, "config", "user.email", "t@t"); _git(repo, "config", "user.name", "t")
    (repo / "x").write_text("x"); _git(repo, "add", "-A"); _git(repo, "commit", "-qm", "base")
    return repo


def _branch(repo):
    return subprocess.run(["git", "-C", str(repo), "branch", "--show-current"],
                          capture_output=True, text=True).stdout.strip()


def test_creates_ticket_first_then_branch(tmp_path, monkeypatch, capsys):
    repo = _repo(tmp_path)
    monkeypatch.chdir(repo)
    monkeypatch.setattr(jira, "create_and_place", lambda *a, **k: (0, "KEEL-999"))
    assert start.main(["My great feature", "--project", "KEEL"]) == 0
    assert _branch(repo) == "feat/KEEL-999-my-great-feature"      # branch named from the new key
    assert "KEEL-999" in capsys.readouterr().out


def test_kind_flag_sets_the_prefix(tmp_path, monkeypatch):
    repo = _repo(tmp_path)
    monkeypatch.chdir(repo)
    monkeypatch.setattr(jira, "create_and_place", lambda *a, **k: (0, "KEEL-7"))
    assert start.main(["fix the bug", "--project", "KEEL", "--kind", "fix"]) == 0
    assert _branch(repo) == "fix/KEEL-7-fix-the-bug"


def test_no_branch_when_ticket_creation_fails(tmp_path, monkeypatch):
    repo = _repo(tmp_path)
    monkeypatch.chdir(repo)
    monkeypatch.setattr(jira, "create_and_place", lambda *a, **k: (1, None))   # create errored red
    assert start.main(["whatever", "--project", "KEEL"]) == 1
    branches = subprocess.run(["git", "-C", str(repo), "branch", "--format=%(refname:short)"],
                              capture_output=True, text=True).stdout
    assert "feat/" not in branches                               # no branch made on a failed create


def test_no_project_errors(tmp_path, monkeypatch, capsys):
    repo = _repo(tmp_path)
    monkeypatch.chdir(repo)                                       # no emkeel.toml, no --project
    assert start.main(["x"]) == 1
    assert "no jira project" in capsys.readouterr().err.lower()
