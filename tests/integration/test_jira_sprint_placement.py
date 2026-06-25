"""Integration: no ticket is orphaned in silence — `emkeel jira create` always recommends + always places.

The 53-orphan incident (ECO tickets left with no sprint) end to end, through the real CLI with only the
Jira HTTP boundary injected. When the project uses sprints, a freshly created ticket ALWAYS gets a surfaced
recommendation and an applied placement — even on the non-interactive agent path (no flag). On Kanban it's
N/A. Stdout stays just the key (scriptable); all sprint messaging is on stderr.
"""

import emkeel.cli as cli
import emkeel.jira as J


def _no_isolation(monkeypatch):
    monkeypatch.setattr(J, "find_identity", lambda p: None)
    for k in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_TOKEN"):
        monkeypatch.setenv(k, "x")


def _caller(monkeypatch, *, board="scrum", active=True, calls=None):
    """Fake Jira: create (201) + the Agile board/sprint/placement endpoints."""
    def caller(method, path, body=None):
        if calls is not None:
            calls.append((method, path))
        if method == "POST" and path == "/rest/api/3/issue":
            return 201, {"key": "ECO-100"}
        if method == "GET" and path.startswith("/rest/agile/1.0/board?"):
            return (200, {"values": []}) if board == "kanban" else (200, {"values": [{"id": 7}]})
        if method == "GET" and "/sprint?state=active" in path:
            return 200, {"values": ([{"id": 42, "name": "Sprint 9"}] if active else [])}
        if method == "POST" and ("/sprint/" in path or path.endswith("/backlog/issue")):
            return 204, {}
        return 200, {}
    monkeypatch.setattr(J, "_default_caller", lambda: caller)
    return caller


def test_agent_create_places_in_active_sprint_never_orphaned(monkeypatch, capsys):
    # the incident's fix on the agent path: no flag, an active sprint running → placed in it + surfaced.
    _no_isolation(monkeypatch)
    calls = []
    _caller(monkeypatch, active=True, calls=calls)
    rc = cli.main(["jira", "create", "--project", "ECO", "--summary", "agent work"])
    assert rc == 0
    out, err = capsys.readouterr()
    assert out.strip() == "ECO-100"                                  # stdout scriptable
    assert "recommended placement" in err and "Sprint 9" in err      # recommendation ALWAYS surfaced
    assert ("POST", "/rest/agile/1.0/sprint/42/issue") in calls      # placement ALWAYS applied


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
    _caller(monkeypatch, board="kanban", calls=calls)
    rc = cli.main(["jira", "create", "--project", "ECO", "--summary", "kanban work"])
    assert rc == 0
    out, err = capsys.readouterr()
    assert out.strip() == "ECO-100" and "recommended" not in err     # sprints don't apply → quiet
    assert not any("/sprint/" in p or p.endswith("/backlog/issue") for _, p in calls)


def test_sprint_flag_overrides_to_backlog_recommendation_still_surfaced(monkeypatch, capsys):
    _no_isolation(monkeypatch)
    calls = []
    _caller(monkeypatch, active=True, calls=calls)
    rc = cli.main(["jira", "create", "--project", "ECO", "--summary", "park it", "--sprint", "backlog"])
    assert rc == 0
    _, err = capsys.readouterr()
    assert "recommended placement" in err and "Sprint 9" in err      # the recommendation is still shown…
    assert ("POST", "/rest/agile/1.0/backlog/issue") in calls        # …but the chosen placement wins
    assert ("POST", "/rest/agile/1.0/sprint/42/issue") not in calls
