"""Tests for the jira-transition automation. Network is injected (no real calls)."""

import emkeel.jira as J
from emkeel.jira import pick_transition, transition_issue

TRANSITIONS = {"transitions": [{"id": "11", "name": "In Progress"}, {"id": "31", "name": "Done"}]}


def test_pick_transition_found_case_insensitive():
    assert pick_transition(TRANSITIONS["transitions"], "done") == "31"


def test_pick_transition_not_found():
    assert pick_transition(TRANSITIONS["transitions"], "Closed") is None


def _caller(get_status=200, get_body=None, post_status=204):
    calls = []

    def caller(method, path, body=None):
        calls.append((method, path, body))
        if method == "GET":
            return get_status, (get_body if get_body is not None else TRANSITIONS)
        return post_status, {}

    caller.calls = calls
    return caller


def test_transition_success():
    c = _caller()
    ok, msg = transition_issue("KEEL-6", "Done", caller=c)
    assert ok and "KEEL-6 -> Done" in msg
    assert c.calls[1][0] == "POST" and c.calls[1][2] == {"transition": {"id": "31"}}


def test_transition_soft_success_when_target_unavailable():
    c = _caller(get_body={"transitions": [{"id": "11", "name": "In Progress"}]})
    ok, msg = transition_issue("KEEL-6", "Done", caller=c)
    assert ok and "skipped" in msg  # already Done? non-blocking


def test_transition_hard_fail_on_read_error():
    ok, msg = transition_issue("KEEL-6", "Done", caller=_caller(get_status=401))
    assert not ok and "cannot read" in msg


def test_transition_hard_fail_on_post_error():
    ok, msg = transition_issue("KEEL-6", "Done", caller=_caller(post_status=400))
    assert not ok and "POST failed" in msg


def test_main_derives_key_from_branch(monkeypatch):
    seen = {}
    monkeypatch.setattr(J, "transition_issue", lambda key, status="Done": (seen.setdefault("key", key), (True, "ok"))[1])
    monkeypatch.setenv("EMKEEL_BRANCH", "feat/KEEL-6-jira-transition")
    monkeypatch.delenv("EMKEEL_PR_TITLE", raising=False)
    assert J.main([]) == 0
    assert seen["key"] == "KEEL-6"


def test_main_fails_without_key(monkeypatch):
    monkeypatch.delenv("EMKEEL_BRANCH", raising=False)
    monkeypatch.delenv("EMKEEL_PR_TITLE", raising=False)
    assert J.main([]) == 1
