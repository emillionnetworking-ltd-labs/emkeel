"""Tests for emkeel connect (gh automation is injected — no real calls)."""

from types import SimpleNamespace

from emkeel.connect import (
    current_branch, do_push, gh_ok, load_config, main, protection_body, repo_exists,
)


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

    answers = iter(["y", "y", "me@x.co", "n"])           # protect? secrets? email; finish-adopt? (no)
    assert main([], inp=lambda *_: next(answers), getpass=lambda *_: "TOK", run=run) == 0
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

    answers = iter(["y", "y", "n", "n"])                  # create+push? protect? secrets?(no) finish-adopt?(no)
    assert main([], inp=lambda *_: next(answers), getpass=lambda *_: "TOK", run=run) == 0
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

    answers = iter(["n", "n", "y"])                       # protect?(no) secrets?(no) finish-adopt?(yes)
    assert main([], inp=lambda *_: next(answers), getpass=lambda *_: "T", run=run) == 0
    joined = "\n".join(ran)
    assert "git push -u origin HEAD" in joined
    assert "pr create --fill" in joined
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

    answers = iter(["n", "n"])                            # protect?(no) secrets?(no) — NO finish-adopt prompt
    assert main([], inp=lambda *_: next(answers), getpass=lambda *_: "T", run=run) == 0
    assert not any("pr merge" in r for r in ran)          # no auto-merge offered on the default branch
