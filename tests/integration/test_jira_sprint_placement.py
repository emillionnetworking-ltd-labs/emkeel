"""Integration: no ticket orphaned in silence — `emkeel jira create` recommends, the OPERATOR places.

End to end through the real CLI with only the Jira HTTP boundary injected. When the project uses sprints
(detected by sprint CAPABILITY on a real-shaped Team-managed board, not `type=scrum`), a freshly created
ticket ALWAYS gets a surfaced recommendation and is left CONSCIOUSLY in the backlog labeled pending — the
sprint placement is the operator's decision (explicit `--sprint`). On Kanban it's N/A. Stdout stays just the
key (scriptable); all sprint messaging is on stderr. Covers the ECO-73 silent-orphan regression.
"""

import re

import emkeel.cli as cli
import emkeel.jira as J


def _no_isolation(monkeypatch):
    monkeypatch.setattr(J, "find_identity", lambda p: None)
    for k in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_TOKEN"):
        monkeypatch.setenv(k, "x")


def _caller(monkeypatch, *, supports=True, active=True, calls=None):
    """Fake Jira: create (201) + the Agile board/sprint/placement/label endpoints. The board is a
    Team-managed 'simple' board (NOT type=scrum); sprint capability is the sprint endpoint answering 200."""
    def caller(method, path, body=None):
        if calls is not None:
            calls.append((method, path))
        if method == "POST" and path == "/rest/api/3/issue":
            return 201, {"key": "ECO-100"}
        if method == "GET" and path.startswith("/rest/agile/1.0/board?"):
            return 200, {"values": [{"id": 100, "type": "simple"}]}      # real ECO shape — not scrum
        if method == "GET" and re.search(r"/board/\d+/sprint", path):
            if "maxResults=1" in path:
                return (200, {"values": []}) if supports else (400, {"errorMessages": ["no sprints"]})
            if "state=active" in path:
                return 200, {"values": ([{"id": 42, "name": "Sprint 9"}] if active else [])}
            return 200, {"values": []}
        if method == "POST" and ("/sprint/" in path or path.endswith("/backlog/issue")):
            return 204, {}
        if method == "PUT" and path.startswith("/rest/api/3/issue/"):
            return 204, {}
        return 200, {}
    monkeypatch.setattr(J, "_default_caller", lambda: caller)
    return caller


def test_agent_create_recommends_and_leaves_pending_never_orphaned(monkeypatch, capsys):
    # ECO-73 regression: a Team-managed board WITH sprints is detected (not Kanban) → recommendation
    # surfaced + ticket left in backlog labeled pending; NEVER auto-placed, NEVER silent.
    _no_isolation(monkeypatch)
    calls = []
    _caller(monkeypatch, supports=True, active=True, calls=calls)
    rc = cli.main(["jira", "create", "--project", "ECO", "--summary", "agent work"])
    assert rc == 0
    out, err = capsys.readouterr()
    assert out.strip() == "ECO-100"                                  # stdout scriptable
    assert "recommended placement" in err and "Sprint 9" in err      # recommendation ALWAYS surfaced
    assert "YOURS to decide" in err                                  # the operator decides
    assert ("POST", "/rest/agile/1.0/sprint/42/issue") not in calls  # NOT auto-placed
    assert ("POST", "/rest/agile/1.0/backlog/issue") in calls        # conscious backlog
    assert any(m == "PUT" and "/issue/ECO-100" in p for m, p in calls)   # labeled pending


def test_create_consciously_backlogs_when_no_active_sprint(monkeypatch, capsys):
    _no_isolation(monkeypatch)
    calls = []
    _caller(monkeypatch, active=False, calls=calls)
    rc = cli.main(["jira", "create", "--project", "ECO", "--summary", "later work"])
    assert rc == 0
    _, err = capsys.readouterr()
    assert "the backlog" in err                                      # recommendation surfaced
    assert ("POST", "/rest/agile/1.0/backlog/issue") in calls        # consciously placed in backlog


def test_create_on_kanban_is_na(monkeypatch, capsys):
    _no_isolation(monkeypatch)
    calls = []
    _caller(monkeypatch, supports=False, calls=calls)
    rc = cli.main(["jira", "create", "--project", "ECO", "--summary", "kanban work"])
    assert rc == 0
    out, err = capsys.readouterr()
    assert out.strip() == "ECO-100" and "recommended" not in err     # sprints don't apply → quiet
    assert not any("/sprint/" in p for _, p in calls)


def test_explicit_sprint_active_is_the_operators_placement(monkeypatch, capsys):
    _no_isolation(monkeypatch)
    calls = []
    _caller(monkeypatch, active=True, calls=calls)
    rc = cli.main(["jira", "create", "--project", "ECO", "--summary", "go", "--sprint", "active"])
    assert rc == 0
    _, err = capsys.readouterr()
    assert "recommended placement" in err                            # still surfaced…
    assert ("POST", "/rest/agile/1.0/sprint/42/issue") in calls      # …operator chose → placed in the sprint
    assert J.PENDING_LABEL not in err                                # not pending
