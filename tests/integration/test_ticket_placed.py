"""Integration: the placed-gate end to end through the REAL jira parsing, with a stub Jira caller.

KEEL-117: `check_ticket_placed` reads the Sprint custom-field id (`/field`), the board's sprint capability,
and the issue's labels/sprint/status — then decides. This injects a fake HTTP caller into the real
`emkeel.jira` functions (no network), so the actual field-discovery + parsing run: a pending, un-sprinted
ticket FAILS the gate; the same ticket once it's in a sprint PASSES.
"""

import emkeel.gates.check_ticket_placed as g
import emkeel.jira as jira

SPRINT_FIELD = "customfield_10020"


def _caller(*, labels, sprints, done=False, supports_sprints=True):
    """A fake Jira HTTP caller covering exactly the endpoints the gate touches."""
    def call(method, path, body=None):
        if path == "/rest/api/3/field":
            return 200, [{"id": SPRINT_FIELD, "name": "Sprint", "custom": True}]
        if path.startswith("/rest/agile/1.0/board?projectKeyOrId="):
            return 200, {"values": [{"id": 100}]}
        if path.startswith("/rest/agile/1.0/board/100/sprint"):
            return (200 if supports_sprints else 400), {"values": []}
        if path.startswith("/rest/api/3/issue/"):
            cat = "done" if done else "indeterminate"
            return 200, {"fields": {"labels": list(labels), SPRINT_FIELD: sprints,
                                    "status": {"statusCategory": {"key": cat}}}}
        return 404, {}
    return call


def _run(monkeypatch, caller, *, branch="feat/ECO-9-x"):
    monkeypatch.setenv("EMKEEL_BRANCH", branch)
    monkeypatch.delenv("EMKEEL_PR_TITLE", raising=False)
    monkeypatch.setattr(jira, "secrets_present", lambda: True)
    monkeypatch.setattr(jira, "_default_caller", lambda: caller)
    return g.main()


def test_pending_unsprinted_fails_real_parsing(monkeypatch, capsys):
    caller = _caller(labels=["emkeel-placement-pending"], sprints=None)
    assert _run(monkeypatch, caller) == 1
    assert "undecided" in capsys.readouterr().err.lower()


def test_placed_in_sprint_passes_real_parsing(monkeypatch):
    caller = _caller(labels=["emkeel-placement-pending"],
                     sprints=[{"id": 1771, "name": "ECO Sprint 5", "state": "active"}])
    assert _run(monkeypatch, caller) == 0                       # in a sprint → decided, even if label lingers


def test_kanban_project_is_na_real_parsing(monkeypatch, capsys):
    caller = _caller(labels=["emkeel-placement-pending"], sprints=None, supports_sprints=False)
    assert _run(monkeypatch, caller) == 0
    assert "kanban" in capsys.readouterr().out.lower()
