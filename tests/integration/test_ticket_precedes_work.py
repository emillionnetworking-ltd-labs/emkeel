"""Integration: ticket-first enforced through the REAL git plumbing.

KEEL-116: `check_ticket_precedes_work` compares Jira's `created` to the branch's first commit author-date.
This drives a real git repo with a fixed commit author-date, monkeypatches only the Jira side (the `created`
timestamp), and runs the gate end to end — so the real `git log --format=%aI` parsing is exercised: a ticket
created BEFORE the commit passes, one created AFTER fails.
"""

import subprocess

import emkeel.gates.check_ticket_precedes_work as g
import emkeel.jira as jira

COMMIT_DATE = "2026-06-26T10:00:00+00:00"   # fixed author-date of the branch's commit


def _git(repo, *args, env=None):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True, env=env)


def _repo_with_dated_commit(tmp_path):
    import os
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q"); _git(repo, "config", "user.email", "t@t"); _git(repo, "config", "user.name", "t")
    (repo / "base").write_text("base"); _git(repo, "add", "-A"); _git(repo, "commit", "-qm", "base")
    _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    _git(repo, "checkout", "-qb", "feat/KEEL-116-x")
    env = {**os.environ, "GIT_AUTHOR_DATE": COMMIT_DATE}          # fix the author-date the gate reads
    (repo / "work").write_text("work"); _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "the work", env=env)
    return repo


def _run_gate(repo, monkeypatch, *, created):
    monkeypatch.chdir(repo)                                       # first_commit_date diffs in cwd
    monkeypatch.setenv("EMKEEL_BRANCH", "feat/KEEL-116-x")
    monkeypatch.setenv("EMKEEL_BASE_REF", "main")
    monkeypatch.delenv("EMKEEL_PR_TITLE", raising=False)
    monkeypatch.setattr(jira, "secrets_present", lambda: True)
    monkeypatch.setattr(jira, "issue_created", lambda key, **k: (200, created))
    return g.main()


def test_ticket_before_commit_passes_real_git(tmp_path, monkeypatch):
    repo = _repo_with_dated_commit(tmp_path)
    assert _run_gate(repo, monkeypatch, created="2026-06-26T09:00:00+00:00") == 0   # ticket 1h before


def test_ticket_after_commit_fails_real_git(tmp_path, monkeypatch, capsys):
    repo = _repo_with_dated_commit(tmp_path)
    assert _run_gate(repo, monkeypatch, created="2026-06-26T11:00:00+00:00") == 1   # ticket 1h after
    assert "after the work" in capsys.readouterr().err.lower()
