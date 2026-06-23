"""Integration: a ticket can't be born Done — `emkeel jira create` never sets status (the ECO-69/70 bug).

End to end through the real CLI with only the Jira HTTP boundary injected: `create --status Done` is
rejected and nothing is POSTed; a normal `create` POSTs the issue (born in the initial state) and never
transitions it; and the legitimate work→merge→Done path via `transition` still moves the issue to Done.
"""

import emkeel.cli as cli
import emkeel.jira as J


def _no_isolation(monkeypatch):
    monkeypatch.setattr(J, "find_identity", lambda p: None)
    for k in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_TOKEN"):
        monkeypatch.setenv(k, "x")


def _record_caller(monkeypatch, *, status_after="To Do"):
    """Inject the HTTP boundary; record every call. Models create (201) + the transition dance."""
    calls = []
    state = {"status": status_after}

    def caller(method, path, body=None):
        calls.append((method, path))
        if method == "POST" and path == "/rest/api/3/issue":
            return 201, {"key": "ECO-70"}
        if method == "GET" and path.endswith("/transitions"):
            return 200, {"transitions": [{"id": "31", "name": "Done"}]}
        if method == "POST" and path.endswith("/transitions"):
            state["status"] = "Done"
            return 204, {}
        if method == "GET" and path.startswith("/rest/api/3/issue/"):
            return 200, {"fields": {"status": {"name": state["status"]}}}
        return 200, {}
    monkeypatch.setattr(J, "_default_caller", lambda: caller)
    return calls


def test_create_status_done_is_blocked_nothing_posted(tmp_path, monkeypatch, capsys):
    _no_isolation(monkeypatch)
    calls = _record_caller(monkeypatch)
    rc = cli.main(["jira", "create", "--project", "ECO", "--summary", "BUILD", "--status", "Done"])
    assert rc == 1
    assert "INITIAL state" in capsys.readouterr().err
    assert calls == []                                         # never touched Jira — rejected before create


def test_normal_create_is_born_initial_never_transitioned(tmp_path, monkeypatch, capsys):
    _no_isolation(monkeypatch)
    calls = _record_caller(monkeypatch)
    rc = cli.main(["jira", "create", "--project", "ECO", "--summary", "real work"])
    assert rc == 0
    assert capsys.readouterr().out.strip() == "ECO-70"
    assert calls == [("POST", "/rest/api/3/issue")]           # created, and NOT transitioned


def test_work_then_merge_then_done_still_transitions(tmp_path, monkeypatch, capsys):
    # the legitimate path is intact: a separate `transition` (post-merge) moves the issue to Done.
    _no_isolation(monkeypatch)
    calls = _record_caller(monkeypatch)
    rc = cli.main(["jira", "ECO-70", "--status", "Done"])
    assert rc == 0
    assert "Done" in capsys.readouterr().out
    assert ("POST", "/rest/api/3/issue/ECO-70/transitions") in calls   # the transition actually happened
