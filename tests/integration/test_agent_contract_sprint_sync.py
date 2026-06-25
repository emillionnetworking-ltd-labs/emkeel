"""Integration: the scaffolded agent contract (AGENTS.md) stays in sync with the real sprint CLI.

The drift this guards against (KEEL-113): the contract said "lands in the active sprint by default" (the
KEEL-106 auto-place text) long after KEEL-111 changed the CLI to recommend-and-leave-pending — so an agent
reading the contract wouldn't surface/ask about placement. We tie the scaffolded contract to the ACTUAL CLI
(its constants + behavior) end to end, so the two can't silently diverge again — the meta-KEEL spirit.
"""

import emkeel.jira as J
from emkeel.init import Config, apply

CFG = Config(jira_url="https://x", jira_project="ECO", github_repo="o/r")


def test_contract_describes_what_the_cli_actually_does(tmp_path, monkeypatch):
    apply(tmp_path, CFG, force=True, dry_run=False)
    agents = (tmp_path / "AGENTS.md").read_text()

    # 1) the contract is tied to the real CLI constant + says the operator decides + pending.
    assert J.PENDING_LABEL in agents
    assert "OPERATOR decides" in agents and "PENDING" in agents and "RELAY" in agents
    assert "lands in the active sprint by default" not in agents      # the stale KEEL-106 promise is gone

    # 2) and that description matches what `emkeel jira create` REALLY does on the default path: an active
    #    sprint exists, no --sprint flag → it does NOT auto-add to the sprint; it leaves the ticket pending.
    monkeypatch.setattr(J, "find_identity", lambda p: None)
    for k in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_TOKEN"):
        monkeypatch.setenv(k, "x")
    monkeypatch.setattr(J, "create_issue", lambda *a, **k: (True, "ECO-200"))
    calls = []

    def caller(method, path, body=None):
        calls.append((method, path))
        if method == "GET" and path.startswith("/rest/agile/1.0/board?"):
            return 200, {"values": [{"id": 100, "type": "simple"}]}
        if method == "GET" and "/sprint" in path:
            if "maxResults=1" in path:
                return 200, {"values": []}
            return 200, {"values": [{"id": 42, "name": "Sprint 9"}]}     # active sprint exists
        return 204, {}
    monkeypatch.setattr(J, "_default_caller", lambda: caller)

    assert J.main(["create", "--project", "ECO", "--summary", "w"]) == 0
    assert ("POST", "/rest/agile/1.0/sprint/42/issue") not in calls     # NOT auto-placed — as the contract says
    assert ("POST", "/rest/agile/1.0/backlog/issue") in calls          # left pending in the backlog
