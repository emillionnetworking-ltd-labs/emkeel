"""emkeel jira place <key> — the operator decides a pending ticket's sprint placement (clears the flag)."""

import emkeel.jira as jira
from emkeel.jira import Placement


def _patch(monkeypatch, *, rec, place_result=(True, "ECO-9 placed in sprint 'S5' (#5)"),
           block=None, secrets=True):
    monkeypatch.setattr(jira, "_isolation_block_project", lambda p: block)
    monkeypatch.setattr(jira, "secrets_present", lambda: secrets)
    monkeypatch.setattr(jira, "_default_caller", lambda: object())
    monkeypatch.setattr(jira, "recommend_placement", lambda project, **k: rec)
    monkeypatch.setattr(jira, "place_issue", lambda key, target, **k: place_result)
    calls = {}
    monkeypatch.setattr(jira, "_unmark_pending", lambda key, **k: (calls.__setitem__("unmark", key), True)[1])
    return calls


def test_place_active_clears_pending(monkeypatch, capsys):
    calls = _patch(monkeypatch, rec=Placement("active_sprint", "x", sprint_id=5, sprint_name="S5"))
    assert jira._main_place(["ECO-9", "--sprint", "active"]) == 0
    assert calls.get("unmark") == "ECO-9"                       # decision made → pending label cleared
    assert "placed" in capsys.readouterr().out.lower()


def test_place_backlog_clears_pending(monkeypatch):
    calls = _patch(monkeypatch, rec=Placement("backlog", "no active sprint"),
                   place_result=(True, "ECO-9 placed in the backlog"))
    assert jira._main_place(["ECO-9", "--sprint", "backlog"]) == 0
    assert calls.get("unmark") == "ECO-9"                       # conscious backlog is also a decision


def test_place_kanban_is_na(monkeypatch, capsys):
    _patch(monkeypatch, rec=Placement("none", "kanban"))
    assert jira._main_place(["ECO-9"]) == 0
    assert "kanban" in capsys.readouterr().out.lower()


def test_place_isolation_blocked(monkeypatch, capsys):
    _patch(monkeypatch, rec=Placement("active_sprint", "x"), block="cross-repo refusal")
    assert jira._main_place(["FOO-1"]) == 1
    assert "cross-repo" in capsys.readouterr().err.lower()


def test_place_dispatch_via_main(monkeypatch):
    _patch(monkeypatch, rec=Placement("active_sprint", "x", sprint_id=5, sprint_name="S5"))
    assert jira.main(["place", "ECO-9"]) == 0                   # `emkeel jira place` routes here
