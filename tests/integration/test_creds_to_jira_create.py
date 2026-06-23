"""Integration: the creds → `emkeel jira create` flow, end to end, WITHOUT direnv.

This is the seed of `tests/integration/` and the example the new gate enforces. It exercises the exact
flow KEEL-93/94 broke and KEEL-102 fixed: a governed repo whose scoped credentials live only in `.env`
(direnv not installed → nothing in the environment) must still create a ticket for its OWN project, while
a cross-project request stays blocked and a no-creds case fails LOUD. The Jira HTTP boundary is the only
thing injected — everything else is the real CLI path (`emkeel.cli.main → jira.main`).
"""

import emkeel.cli as cli
import emkeel.jira as J


def _governed_repo(tmp_path, project="DEMO", *, env=True):
    (tmp_path / "emkeel.toml").write_text(
        f'[jira]\nbase_url = "https://x.atlassian.net"\nproject_key = "{project}"\n[github]\nrepo = "o/r"\n')
    if env:
        (tmp_path / ".env").write_text(
            "GH_TOKEN=github_pat_x\nJIRA_BASE_URL=https://x.atlassian.net\n"
            "JIRA_EMAIL=me@x.co\nJIRA_TOKEN=jt-secret\n")


def _no_env_creds(monkeypatch):
    for k in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_TOKEN", "GH_TOKEN"):
        monkeypatch.delenv(k, raising=False)


def _fake_jira(monkeypatch, created_key="DEMO-1"):
    """Inject ONLY the HTTP boundary: POST /issue → 201 {key}. Records the project it was asked for."""
    seen = {}

    def caller(method, path, body=None):
        if method == "POST" and path == "/rest/api/3/issue":
            seen["project"] = body["fields"]["project"]["key"]
            return 201, {"key": created_key}
        return 200, {}
    monkeypatch.setattr(J, "_default_caller", lambda: caller)
    return seen


def test_create_succeeds_from_scoped_env_without_direnv(tmp_path, monkeypatch, capsys):
    # no creds in the environment (direnv never loaded .env) — they live only in the repo's .env.
    _governed_repo(tmp_path, "DEMO", env=True)
    monkeypatch.chdir(tmp_path)
    _no_env_creds(monkeypatch)
    seen = _fake_jira(monkeypatch, "DEMO-7")

    rc = cli.main(["jira", "create", "--project", "DEMO", "--summary", "real e2e"])

    assert rc == 0
    assert seen.get("project") == "DEMO"                       # reached Jira with the right project
    assert capsys.readouterr().out.strip().endswith("DEMO-7")  # the new key printed


def test_cross_project_still_blocked_even_with_scoped_env(tmp_path, monkeypatch, capsys):
    # isolation is untouched: the scoped .env does NOT relax the guard.
    _governed_repo(tmp_path, "DEMO", env=True)
    monkeypatch.chdir(tmp_path)
    _no_env_creds(monkeypatch)
    seen = _fake_jira(monkeypatch)

    rc = cli.main(["jira", "create", "--project", "ECO", "--summary", "cross"])

    assert rc == 1
    assert "isolation" in capsys.readouterr().err
    assert "project" not in seen                               # never reached Jira


def test_no_creds_fails_loud_not_silent(tmp_path, monkeypatch, capsys):
    # no environment creds AND no .env → hard, visible failure (never a silent skip).
    _governed_repo(tmp_path, "DEMO", env=False)
    monkeypatch.chdir(tmp_path)
    _no_env_creds(monkeypatch)

    rc = cli.main(["jira", "create", "--project", "DEMO", "--summary", "x"])

    assert rc == 1
    err = capsys.readouterr().err
    assert "::error::" in err and "STOP" in err
