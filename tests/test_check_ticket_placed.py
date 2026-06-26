"""check_ticket_placed — a sprint-project ticket must have its placement DECIDED before merge."""

import emkeel.gates.check_ticket_placed as g
import emkeel.jira as jira

_PENDING = {"pending_label": True, "in_sprint": False, "done": False}


def _run(monkeypatch, *, branch="feat/ECO-9-x", pr_title="", secrets=True, board=100, reachable=True,
         state=None, status=200):
    monkeypatch.setenv("EMKEEL_BRANCH", branch)
    monkeypatch.setenv("EMKEEL_PR_TITLE", pr_title)
    monkeypatch.setattr(jira, "secrets_present", lambda: secrets)
    monkeypatch.setattr(jira, "_default_caller", lambda: object())
    monkeypatch.setattr(jira, "_sprint_board", lambda project, **k: (board, reachable))
    monkeypatch.setattr(jira, "issue_placement_state",
                        lambda key, **k: (status, _PENDING if state is None else state))
    return g.main()


def test_pending_and_not_in_sprint_fails(monkeypatch, capsys):
    assert _run(monkeypatch, state={"pending_label": True, "in_sprint": False, "done": False}) == 1
    assert "undecided" in capsys.readouterr().err.lower()


def test_in_sprint_passes(monkeypatch):
    # placed in a sprint (however it got there) → decided → OK, even if the label lingers.
    assert _run(monkeypatch, state={"pending_label": True, "in_sprint": True, "done": False}) == 0


def test_label_removed_passes(monkeypatch):
    # conscious backlog decision: the pending label is gone → OK even without a sprint.
    assert _run(monkeypatch, state={"pending_label": False, "in_sprint": False, "done": False}) == 0


def test_done_is_na(monkeypatch):
    assert _run(monkeypatch, state={"pending_label": True, "in_sprint": False, "done": True}) == 0


def test_kanban_is_na(monkeypatch):
    assert _run(monkeypatch, board=None) == 0                    # no sprint board → placement N/A


def test_maint_lane_is_na(monkeypatch):
    assert _run(monkeypatch, branch="emkeel-maint/refresh") == 0


def test_dependabot_lane_is_na(monkeypatch):
    assert _run(monkeypatch, branch="dependabot/pip/x") == 0


def test_no_key_is_na(monkeypatch):
    assert _run(monkeypatch, branch="feat/no-key") == 0


def test_no_secrets_is_inconclusive(monkeypatch):
    assert _run(monkeypatch, secrets=False) == 0                 # would FAIL if checked; skipped w/o secrets


def test_agile_unreachable_is_inconclusive(monkeypatch):
    assert _run(monkeypatch, reachable=False) == 0


def test_jira_read_error_is_inconclusive(monkeypatch):
    assert _run(monkeypatch, status=500, state=None) == 0
