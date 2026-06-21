"""Tests for emkeel connect (gh automation is injected — no real calls)."""

from types import SimpleNamespace

import pytest

from emkeel.connect import (
    allow_auto_merge, current_branch, do_push, gh_ok, load_config, main, protection_body,
    repo_exists, verify_jira,
)


@pytest.fixture(autouse=True)
def _stub_jira_verify(monkeypatch):
    # connect now verifies Jira creds before saving; stub the network call so tests stay offline.
    monkeypatch.setattr("emkeel.connect._jira_fetch", lambda b, e, t: (True, "tester"))


def _ok(stdout="ok"):
    return SimpleNamespace(returncode=0, stdout=stdout, stderr="")


def _fail(stderr="nope"):
    return SimpleNamespace(returncode=1, stdout="", stderr=stderr)


def _toml(p, repo="a/b", base="https://x.atlassian.net"):
    (p / "emkeel.toml").write_text(f'[github]\nrepo = "{repo}"\n[jira]\nbase_url = "{base}"\n')


def test_load_config(tmp_path):
    _toml(tmp_path)
    cfg = load_config(tmp_path)
    assert cfg.repo == "a/b" and cfg.base_url == "https://x.atlassian.net"


def test_load_config_missing(tmp_path):
    assert load_config(tmp_path) is None


def test_protection_body():
    b = protection_body()
    assert b["required_status_checks"]["contexts"] == ["gates"]
    assert b["required_pull_request_reviews"]["required_approving_review_count"] == 0  # solo-friendly
    assert b["restrictions"] is None


def test_gh_helpers():
    assert gh_ok(run=lambda *a, **k: _ok()) is True
    assert gh_ok(run=lambda *a, **k: _fail()) is False
    assert repo_exists("a/b", run=lambda *a, **k: _ok()) is True


def test_dry_run_runs_nothing(tmp_path, monkeypatch, capsys):
    _toml(tmp_path)
    monkeypatch.chdir(tmp_path)
    calls = []
    assert main(["--dry-run"], run=lambda *a, **k: calls.append(a) or _ok()) == 0
    assert calls == []                                   # dry-run executes nothing
    out = capsys.readouterr().out
    assert "gh repo create" in out and "protection" in out and "JIRA_TOKEN" in out


def test_no_toml_tells_setup(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main([], run=lambda *a, **k: _ok()) == 1
    assert "emkeel setup" in capsys.readouterr().out


def test_existing_repo_flow(tmp_path, monkeypatch, capsys):
    _toml(tmp_path)
    monkeypatch.chdir(tmp_path)
    ran = []

    def run(args, stdin=None):
        ran.append(" ".join(args))
        return _ok()

    answers = iter(["y", "y", "me@x.co", "n", "n"])      # protect? secrets? email; local-cred?(no) finish-adopt?(no)
    assert main([], inp=lambda *_: next(answers), getpass=lambda *_: "TOK", run=run, lang="en") == 0
    joined = "\n".join(ran)
    assert "repo view a/b" in joined                      # checked existence (existing → skip create)
    assert "branches/main/protection" in joined          # set protection
    assert "secret set JIRA_TOKEN" in joined             # set secrets
    assert "branch protection on" in capsys.readouterr().out


def test_new_repo_creates_and_pushes(tmp_path, monkeypatch):
    _toml(tmp_path)
    monkeypatch.chdir(tmp_path)
    ran = []

    def run(args, stdin=None):
        joined = " ".join(args)
        ran.append(joined)
        return _fail() if "repo view" in joined else _ok()   # not on GitHub yet

    answers = iter(["y", "y", "n", "n", "n"])             # create+push? protect? secrets?(no) local-cred?(no) finish-adopt?(no)
    assert main([], inp=lambda *_: next(answers), getpass=lambda *_: "TOK", run=run, lang="en") == 0
    assert any("repo create a/b" in r and "--push" in r for r in ran)   # created + pushed


def test_current_branch():
    assert current_branch(run=lambda *a, **k: SimpleNamespace(returncode=0, stdout="feat/x\n", stderr="")) == "feat/x"


def test_do_push_timeout():
    import subprocess

    def run(*a, **k):
        raise subprocess.TimeoutExpired(cmd="git push", timeout=180)

    ok, msg = do_push(run=run)
    assert ok is False and "timed out" in msg


def test_finish_adopt_pushes_pr_and_automerges(tmp_path, monkeypatch):
    _toml(tmp_path)
    monkeypatch.chdir(tmp_path)
    ran = []

    def run(args, stdin=None, timeout=None, capture=True):
        joined = " ".join(args)
        ran.append(joined)
        if "rev-parse" in joined:
            return SimpleNamespace(returncode=0, stdout="chore/SCRUM-1-adopt-emkeel", stderr="")
        return _ok()

    answers = iter(["n", "n", "n", "y", "n"])             # protect?(no) secrets?(no) local-cred?(no) finish-adopt?(yes) wait-sync?(no)
    assert main([], inp=lambda *_: next(answers), getpass=lambda *_: "T", run=run, lang="en") == 0
    joined = "\n".join(ran)
    assert "git push -u origin HEAD" in joined
    assert "pr create --fill" in joined
    assert "allow_auto_merge=true" in joined              # repo setting enabled first
    assert "pr merge --auto --squash" in joined          # native auto-merge (waits for gates)


def test_finish_adopt_skipped_on_default_branch(tmp_path, monkeypatch):
    _toml(tmp_path)
    monkeypatch.chdir(tmp_path)
    ran = []

    def run(args, stdin=None, timeout=None, capture=True):
        joined = " ".join(args)
        ran.append(joined)
        if "rev-parse" in joined:
            return SimpleNamespace(returncode=0, stdout="main", stderr="")   # on the default branch
        return _ok()

    answers = iter(["n", "n", "n"])                       # protect?(no) secrets?(no) local-cred?(no) — NO finish-adopt prompt
    assert main([], inp=lambda *_: next(answers), getpass=lambda *_: "T", run=run, lang="en") == 0
    assert not any("pr merge" in r for r in ran)          # no auto-merge offered on the default branch


def test_allow_auto_merge_patches_repo():
    calls = []
    allow_auto_merge("a/b", run=lambda args, **k: calls.append(" ".join(args)) or _ok())
    assert "api -X PATCH repos/a/b -F allow_auto_merge=true" in calls[0]


def test_verify_jira_valid():
    ok, detail = verify_jira("https://x.atlassian.net", "me@x.co", "tok",
                             fetch=lambda b, e, t: (True, "Ada Lovelace"))
    assert ok is True and detail == "Ada Lovelace"


def test_verify_jira_invalid():
    ok, detail = verify_jira("https://x.atlassian.net", "me@x.co", "bad",
                             fetch=lambda b, e, t: (False, "HTTP 401"))
    assert ok is False and "401" in detail


def test_secrets_not_saved_when_jira_login_fails(tmp_path, monkeypatch):
    _toml(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("emkeel.connect._jira_fetch", lambda b, e, t: (False, "HTTP 401"))
    ran = []
    def run(args, stdin=None, timeout=None, capture=True):
        ran.append(" ".join(args))
        if "rev-parse" in " ".join(args):
            return SimpleNamespace(returncode=0, stdout="main", stderr="")  # on default → no finish-adopt
        return _ok()
    # protect?(n) secrets?(y) email, [verify fails] retry?(n) local-cred?(n)
    answers = iter(["n", "y", "me@x.co", "n", "n"])
    assert main([], inp=lambda *_: next(answers), getpass=lambda *_: "bad", run=run, lang="en") == 0
    assert not any("secret set JIRA_TOKEN" in r for r in ran)   # never saved the bad creds


# ── scoped local credential (.env) — KEEL-93 ──────────────────────────────────

import os
import stat

from emkeel.connect import write_env


def test_write_env_creates_600_and_idempotent(tmp_path):
    p = write_env(tmp_path, {"GH_TOKEN": "github_pat_abc", "JIRA_TOKEN": "jt"})
    assert p == tmp_path / ".env"
    assert "GH_TOKEN=github_pat_abc" in p.read_text() and "JIRA_TOKEN=jt" in p.read_text()
    assert stat.S_IMODE(os.stat(p).st_mode) == 0o600                  # owner-only
    write_env(tmp_path, {"GH_TOKEN": "github_pat_abc", "JIRA_TOKEN": "jt"})   # re-run
    assert p.read_text().count("GH_TOKEN=") == 1                      # idempotent, no duplicates


def test_write_env_preserves_other_vars(tmp_path):
    (tmp_path / ".env").write_text("MY_OWN=keepme\nGH_TOKEN=old\n")
    write_env(tmp_path, {"GH_TOKEN": "new"})
    body = (tmp_path / ".env").read_text()
    assert "MY_OWN=keepme" in body                                    # untouched user var
    assert "GH_TOKEN=new" in body and "GH_TOKEN=old" not in body      # updated in place


def test_connect_local_cred_writes_env_hidden_pat(tmp_path, monkeypatch, capsys):
    _toml(tmp_path)
    monkeypatch.chdir(tmp_path)

    def run(args, stdin=None, timeout=None, capture=True):
        if "rev-parse" in " ".join(args):
            return SimpleNamespace(returncode=0, stdout="main", stderr="")   # default branch → no finish
        return _ok()

    pats = iter(["github_pat_SCOPED"])                    # the hidden PAT paste (getpass)
    # protect?(n) secrets?(n) local-cred?(y)
    answers = iter(["n", "n", "y"])
    assert main([], inp=lambda *_: next(answers), getpass=lambda *_: next(pats), run=run, lang="en") == 0
    env = (tmp_path / ".env").read_text()
    assert "GH_TOKEN=github_pat_SCOPED" in env                        # the scoped PAT landed in .env
    assert stat.S_IMODE(os.stat(tmp_path / ".env").st_mode) == 0o600
    out = capsys.readouterr().out
    assert "direnv allow" in out and "github_pat_SCOPED" not in out   # guided activation; PAT never echoed


def test_dry_run_mentions_scoped_local_credential(tmp_path, monkeypatch, capsys):
    _toml(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert main(["--dry-run"], run=lambda *a, **k: _ok()) == 0
    out = capsys.readouterr().out
    assert ".env" in out and "GH_TOKEN" in out and "direnv" in out
