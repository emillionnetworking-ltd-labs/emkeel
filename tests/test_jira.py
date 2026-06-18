"""Tests for the jira-transition automation. Network is injected (no real calls)."""

import emkeel.jira as J
from emkeel.jira import create_issue, issue_status, pick_transition, transition_issue

TRANSITIONS = {"transitions": [{"id": "11", "name": "In Progress"}, {"id": "31", "name": "Done"}]}


def test_pick_transition_found_case_insensitive():
    assert pick_transition(TRANSITIONS["transitions"], "done") == "31"


def test_pick_transition_not_found():
    assert pick_transition(TRANSITIONS["transitions"], "Closed") is None


def _caller(transitions_status=200, transitions_body=None, post_status=204,
            verify_status=200, verify_name="Done"):
    """Path-aware fake: /transitions (list), POST (transition), and the verify GET (?fields=status)."""
    calls = []

    def caller(method, path, body=None):
        calls.append((method, path, body))
        if method == "GET" and path.endswith("/transitions"):
            return transitions_status, (transitions_body if transitions_body is not None else TRANSITIONS)
        if method == "GET" and "fields=status" in path:               # the verification read-back
            return verify_status, {"fields": {"status": {"name": verify_name}}}
        return post_status, {}                                        # the transition POST

    caller.calls = calls
    return caller


def test_transition_success_is_verified():
    c = _caller()
    ok, msg = transition_issue("KEEL-6", "Done", caller=c)
    assert ok and "KEEL-6 -> Done (verified)" in msg
    assert c.calls[1][0] == "POST" and c.calls[1][2] == {"transition": {"id": "31"}}
    assert c.calls[2][0] == "GET" and "fields=status" in c.calls[2][1]   # verified by reading back


def test_transition_benign_already_done_is_verified():
    # target transition not offered, but the issue really IS Done → benign soft-success (confirmed).
    c = _caller(transitions_body={"transitions": [{"id": "11", "name": "In Progress"}]}, verify_name="Done")
    ok, msg = transition_issue("KEEL-6", "Done", caller=c)
    assert ok and "already Done (verified)" in msg


def test_transition_not_offered_and_not_done_is_real_fail():
    # target not offered AND the issue is stuck elsewhere → REAL failure, surfaced (not swallowed).
    c = _caller(transitions_body={"transitions": [{"id": "11", "name": "In Progress"}]}, verify_name="In Progress")
    ok, msg = transition_issue("KEEL-6", "Done", caller=c)
    assert not ok and "not Done" in msg


def test_transition_post_ok_but_status_didnt_land_is_fail():
    c = _caller(verify_name="In Progress")        # POST returns 204 but status never became Done
    ok, msg = transition_issue("KEEL-6", "Done", caller=c)
    assert not ok and "status is 'In Progress'" in msg


def test_transition_hard_fail_on_404():
    ok, msg = transition_issue("KEEL-6", "Done", caller=_caller(transitions_status=404))
    assert not ok and "not found" in msg


def test_transition_hard_fail_on_read_error():
    ok, msg = transition_issue("KEEL-6", "Done", caller=_caller(transitions_status=401))
    assert not ok and "cannot read" in msg


def test_transition_hard_fail_on_post_error():
    ok, msg = transition_issue("KEEL-6", "Done", caller=_caller(post_status=400))
    assert not ok and "POST failed" in msg


def test_transition_verify_false_skips_readback():
    c = _caller()
    ok, msg = transition_issue("KEEL-6", "Done", caller=c, verify=False)
    assert ok and msg == "KEEL-6 -> Done" and len(c.calls) == 2   # no verify GET


# ── create_issue + issue_status ────────────────────────────────────────────────

def test_create_issue_returns_key():
    def caller(method, path, body=None):
        assert method == "POST" and path == "/rest/api/3/issue"
        assert body["fields"]["project"]["key"] == "ECO" and body["fields"]["issuetype"]["name"] == "Task"
        return 201, {"key": "ECO-42"}
    ok, res = create_issue("ECO", "do a thing", caller=caller)
    assert ok and res == "ECO-42"


def test_create_issue_includes_adf_description():
    seen = {}
    def caller(method, path, body=None):
        seen["body"] = body
        return 201, {"key": "ECO-43"}
    create_issue("ECO", "s", "Task", "the why", caller=caller)
    assert seen["body"]["fields"]["description"]["type"] == "doc"


def test_create_issue_failure_surfaces():
    ok, res = create_issue("ECO", "s", caller=lambda *a, **k: (400, {"error": "bad"}))
    assert not ok and "create failed (HTTP 400)" in res


def test_issue_status_codes():
    assert issue_status("ECO-1", caller=lambda *a, **k: (200, {"fields": {}})) == 200
    assert issue_status("ECO-9999", caller=lambda *a, **k: (404, {"error": "x"})) == 404


def test_main_derives_key_from_branch(monkeypatch):
    seen = {}
    for k in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_TOKEN"):
        monkeypatch.setenv(k, "x")   # past the secrets guard so main reaches transition_issue
    monkeypatch.setattr(J, "transition_issue", lambda key, status="Done", **kw: (seen.setdefault("key", key), (True, "ok"))[1])
    monkeypatch.setenv("EMKEEL_BRANCH", "feat/KEEL-6-jira-transition")
    monkeypatch.delenv("EMKEEL_PR_TITLE", raising=False)
    assert J.main([]) == 0
    assert seen["key"] == "KEEL-6"


def test_main_fails_without_key(monkeypatch):
    monkeypatch.delenv("EMKEEL_BRANCH", raising=False)
    monkeypatch.delenv("EMKEEL_PR_TITLE", raising=False)
    assert J.main([]) == 1


def test_secrets_present(monkeypatch):
    for k in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_TOKEN"):
        monkeypatch.delenv(k, raising=False)
    assert J.secrets_present() is False
    for k in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_TOKEN"):
        monkeypatch.setenv(k, "x")
    assert J.secrets_present() is True


def test_main_warns_and_skips_without_secrets(monkeypatch, capsys):
    for k in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_TOKEN"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("EMKEEL_BRANCH", "feat/SCRUM-9-x")
    assert J.main([]) == 0                       # non-blocking: graceful skip
    out = capsys.readouterr().out
    assert "::warning::" in out and "secrets" in out.lower()


def test_main_real_failure_emits_error_annotation(monkeypatch, capsys):
    for k in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_TOKEN"):
        monkeypatch.setenv(k, "x")
    monkeypatch.setenv("EMKEEL_BRANCH", "feat/KEEL-6-x")
    monkeypatch.setattr(J, "transition_issue", lambda *a, **k: (False, "KEEL-6: issue not found (HTTP 404)"))
    assert J.main([]) == 1                        # real failure → red
    assert "::error::" in capsys.readouterr().err


# ── `emkeel jira create` CLI ───────────────────────────────────────────────────

def test_cli_create_prints_key(monkeypatch, capsys):
    for k in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_TOKEN"):
        monkeypatch.setenv(k, "x")
    monkeypatch.setattr(J, "create_issue", lambda *a, **k: (True, "ECO-42"))
    assert J.main(["create", "--project", "ECO", "--summary", "do it"]) == 0
    assert capsys.readouterr().out.strip().endswith("ECO-42")


def test_cli_create_requires_secrets(monkeypatch, capsys):
    for k in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_TOKEN"):
        monkeypatch.delenv(k, raising=False)
    assert J.main(["create", "--project", "ECO", "--summary", "x"]) == 1
    assert "::error::" in capsys.readouterr().err


def test_cli_create_then_transition(monkeypatch, capsys):
    for k in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_TOKEN"):
        monkeypatch.setenv(k, "x")
    monkeypatch.setattr(J, "create_issue", lambda *a, **k: (True, "ECO-50"))
    seen = {}
    monkeypatch.setattr(J, "transition_issue", lambda key, status="Done", **k: (seen.update(key=key, status=status), (True, "ok"))[1])
    assert J.main(["create", "--project", "ECO", "--summary", "x", "--status", "Done"]) == 0
    assert seen == {"key": "ECO-50", "status": "Done"}
