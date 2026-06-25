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


def test_main_skips_on_maint_lane(monkeypatch, capsys):
    # THE BUG: emkeel update/set merge on emkeel-maint/* — no ticket to transition → SKIP (exit 0),
    # not a false-red exit 1. (Must not even reach transition_issue.)
    monkeypatch.setattr(J, "transition_issue", lambda *a, **k: (_ for _ in ()).throw(AssertionError("called")))
    monkeypatch.setenv("EMKEEL_BRANCH", "emkeel-maint/0.1.69-abc123")
    monkeypatch.delenv("EMKEEL_PR_TITLE", raising=False)
    assert J.main([]) == 0
    assert "maintenance lane" in capsys.readouterr().out.lower()


def test_main_skips_on_dependabot_lane(monkeypatch, capsys):
    # Same false-red avoidance for the bot lane: no ticket → SKIP exit 0, never reaching transition_issue.
    monkeypatch.setattr(J, "transition_issue", lambda *a, **k: (_ for _ in ()).throw(AssertionError("called")))
    monkeypatch.setenv("EMKEEL_BRANCH", "dependabot/pip/urllib3-2.2.2")
    monkeypatch.delenv("EMKEEL_PR_TITLE", raising=False)
    assert J.main([]) == 0
    assert "dependabot lane" in capsys.readouterr().out.lower()


def test_secrets_present(monkeypatch):
    for k in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_TOKEN"):
        monkeypatch.delenv(k, raising=False)
    assert J.secrets_present() is False
    for k in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_TOKEN"):
        monkeypatch.setenv(k, "x")
    assert J.secrets_present() is True


def test_main_warns_and_skips_without_secrets(monkeypatch, capsys):
    monkeypatch.setattr(J, "find_identity", lambda p: None)   # ungoverned cwd → isolation guard off
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
    monkeypatch.setattr(J, "find_identity", lambda p: None)   # ungoverned cwd → guard off
    for k in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_TOKEN"):
        monkeypatch.setenv(k, "x")
    monkeypatch.setattr(J, "create_issue", lambda *a, **k: (True, "ECO-42"))
    assert J.main(["create", "--project", "ECO", "--summary", "do it"]) == 0
    assert capsys.readouterr().out.strip().endswith("ECO-42")


def test_cli_create_requires_secrets(monkeypatch, capsys):
    monkeypatch.setattr(J, "find_identity", lambda p: None)
    for k in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_TOKEN"):
        monkeypatch.delenv(k, raising=False)
    assert J.main(["create", "--project", "ECO", "--summary", "x"]) == 1
    assert "::error::" in capsys.readouterr().err


def test_cli_create_lands_in_initial_state(monkeypatch, capsys):
    # a normal create makes the issue and NEVER transitions it — it is born in the project's initial state.
    monkeypatch.setattr(J, "find_identity", lambda p: None)
    for k in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_TOKEN"):
        monkeypatch.setenv(k, "x")
    monkeypatch.setattr(J, "create_issue", lambda *a, **k: (True, "ECO-50"))
    monkeypatch.setattr(J, "transition_issue",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("create must not transition")))
    monkeypatch.setattr(J, "_place_after_create", lambda *a: None)   # sprint placement tested separately
    assert J.main(["create", "--project", "ECO", "--summary", "x"]) == 0
    assert capsys.readouterr().out.strip() == "ECO-50"


def test_cli_create_refuses_status_done(monkeypatch, capsys):
    # THE BUG (ECO-69/70): a ticket must not be born Done — create --status Done is rejected, nothing created.
    monkeypatch.setattr(J, "find_identity", lambda p: None)
    for k in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_TOKEN"):
        monkeypatch.setenv(k, "x")
    created = {"n": 0}
    monkeypatch.setattr(J, "create_issue", lambda *a, **k: (created.update(n=1), (True, "ECO-70"))[1])
    assert J.main(["create", "--project", "ECO", "--summary", "build", "--status", "Done"]) == 1
    err = capsys.readouterr().err
    assert "::error::" in err and "INITIAL state" in err and "--status" in err
    assert created["n"] == 0                                   # never created — rejected BEFORE create


# ── isolation: the CLI guard refuses a cross-project jira action (defense in depth) ──

def test_cli_create_blocks_cross_project(monkeypatch, capsys):
    monkeypatch.setattr(J, "find_identity", lambda p: {"repo": "o/emkeel", "project_key": "KEEL", "root": "."})
    for k in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_TOKEN"):
        monkeypatch.setenv(k, "x")
    called = {"n": 0}
    monkeypatch.setattr(J, "create_issue", lambda *a, **k: (called.update(n=1), (True, "ECO-9"))[1])
    assert J.main(["create", "--project", "ECO", "--summary", "x"]) == 1      # KEEL repo → ECO refused
    assert "isolation" in capsys.readouterr().err and called["n"] == 0        # never reached create
    # its own project is fine
    monkeypatch.setattr(J, "create_issue", lambda *a, **k: (True, "KEEL-9"))
    assert J.main(["create", "--project", "KEEL", "--summary", "x"]) == 0


def test_cli_transition_blocks_cross_project(monkeypatch, capsys):
    monkeypatch.setattr(J, "find_identity", lambda p: {"repo": "o/emkeel", "project_key": "KEEL", "root": "."})
    for k in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_TOKEN"):
        monkeypatch.setenv(k, "x")
    monkeypatch.setenv("EMKEEL_BRANCH", "feat/ECO-7-x")
    monkeypatch.setattr(J, "transition_issue", lambda *a, **k: (_ for _ in ()).throw(AssertionError("called")))
    assert J.main([]) == 1                                                    # ECO-7 in a KEEL repo → refused
    assert "isolation" in capsys.readouterr().err


# ── scoped-cred loading without direnv (KEEL-102): the exact gap that let a PR ship with no ticket ──

def _governed_repo_with_env(tmp_path, project="DEMO", env=True):
    (tmp_path / "emkeel.toml").write_text(
        f'[jira]\nbase_url = "https://x.atlassian.net"\nproject_key = "{project}"\n[github]\nrepo = "o/r"\n')
    if env:
        (tmp_path / ".env").write_text(
            "GH_TOKEN=github_pat_x\nJIRA_BASE_URL=https://x.atlassian.net\n"
            "JIRA_EMAIL=me@x.co\nJIRA_TOKEN=jt-secret\n")


def _no_jira_env(monkeypatch):
    for k in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_TOKEN"):
        monkeypatch.delenv(k, raising=False)


def test_create_reads_scoped_env_when_direnv_absent(tmp_path, monkeypatch):
    # THE REGRESSION: no creds in the environment (direnv never loaded .env), but the repo's scoped .env
    # has them → `emkeel jira create --project <own>` reads it in-process and SUCCEEDS.
    _governed_repo_with_env(tmp_path, "DEMO", env=True)
    monkeypatch.chdir(tmp_path)
    _no_jira_env(monkeypatch)                                     # nothing in the environment
    assert J.secrets_present() is True                           # …yet creds resolve, via the scoped .env
    seen = {}
    monkeypatch.setattr(J, "create_issue", lambda *a, **k: (seen.update(reached=True), (True, "DEMO-1"))[1])
    assert J.main(["create", "--project", "DEMO", "--summary", "x"]) == 0
    assert seen.get("reached") is True                           # creds found → create proceeded


def test_scoped_env_does_not_relax_isolation(tmp_path, monkeypatch, capsys):
    # AISLACIÓN INTACTA: even with the scoped .env present, a cross-project create is still BLOCKED.
    _governed_repo_with_env(tmp_path, "DEMO", env=True)
    monkeypatch.chdir(tmp_path)
    _no_jira_env(monkeypatch)
    called = {"n": 0}
    monkeypatch.setattr(J, "create_issue", lambda *a, **k: (called.update(n=1), (True, "ECO-9"))[1])
    assert J.main(["create", "--project", "ECO", "--summary", "x"]) == 1     # DEMO repo → ECO refused
    assert "isolation" in capsys.readouterr().err and called["n"] == 0       # guard fired BEFORE creds/create


def test_create_hard_fails_without_any_creds(tmp_path, monkeypatch, capsys):
    # FALLO DURO no-silencioso: no env AND no .env → red error + exit!=0 (never a silent skip).
    _governed_repo_with_env(tmp_path, "DEMO", env=False)          # no .env written
    monkeypatch.chdir(tmp_path)
    _no_jira_env(monkeypatch)
    assert J.secrets_present() is False
    rc = J.main(["create", "--project", "DEMO", "--summary", "x"])
    assert rc == 1                                               # exit != 0
    err = capsys.readouterr().err
    assert "::error::" in err and "STOP" in err                  # loud + tells the agent to stop


def test_scoped_env_values_is_failsafe_when_ungoverned(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)                                   # no emkeel.toml → no identity
    assert J._scoped_env_values() == {}                          # never raises, empty


# ── sprint placement (KEEL-106/111): detect by capability; recommend but the operator decides ──

def _agile_caller(*, supports=True, board_type="simple", active=True, place_ok=True, label_ok=True,
                  pending=None, boards_status=200, calls=None):
    """A fake Jira Agile caller modeling the REAL shape: the board is `simple` (Team-managed, NOT
    type=scrum) and sprint-capable is decided by the sprint endpoint (200=supports, 400=Kanban). Records
    (method, path) in `calls`."""
    import re as _re
    def caller(method, path, body=None):
        if calls is not None:
            calls.append((method, path))
        if method == "GET" and path.startswith("/rest/agile/1.0/board?"):
            if boards_status != 200:
                return boards_status, {}
            return 200, {"values": [{"id": 100, "type": board_type}]}     # NOT type=scrum
        if method == "GET" and _re.search(r"/board/\d+/sprint", path):
            if "maxResults=1" in path:                                    # the capability probe
                return (200, {"values": []}) if supports else (400, {"errorMessages": ["does not support sprints"]})
            if "state=active" in path:
                return 200, {"values": ([{"id": 42, "name": "Sprint 9"}] if active else [])}
            return 200, {"values": []}
        if method == "POST" and ("/sprint/" in path or path.endswith("/backlog/issue")):
            return (204 if place_ok else 403), {}
        if method == "PUT" and path.startswith("/rest/api/3/issue/"):
            return (204 if label_ok else 400), {}
        if method == "GET" and path.startswith("/rest/api/3/search"):
            return 200, {"issues": [{"key": k} for k in (pending or [])]}
        return 200, {}
    return caller


def test_detects_sprints_on_a_non_scrum_board():
    # THE BUG: ECO's board 100 is 'simple'/Team-managed WITH sprints — type=scrum missed it.
    # Detection by capability recognizes it → recommends the active sprint, not Kanban.
    rec = J.recommend_placement("ECO", caller=_agile_caller(board_type="simple", supports=True, active=True))
    assert rec.kind == "active_sprint" and rec.sprint_id == 42


def test_recommend_backlog_when_no_active_sprint():
    rec = J.recommend_placement("ECO", caller=_agile_caller(active=False))
    assert rec.kind == "backlog"


def test_recommend_none_on_real_kanban_board():
    # a board that does NOT support sprints (sprint endpoint → 400) → genuine Kanban.
    rec = J.recommend_placement("ECO", caller=_agile_caller(supports=False))
    assert rec.kind == "none"


def test_recommend_indeterminate_when_boards_unreadable():
    rec = J.recommend_placement("ECO", caller=_agile_caller(boards_status=503))
    assert rec.kind == "indeterminate"


def test_place_issue_adds_to_active_sprint():
    calls = []
    rec = J.Placement("active_sprint", "x", sprint_id=42, sprint_name="Sprint 9")
    ok, msg = J.place_issue("ECO-1", rec, caller=_agile_caller(calls=calls))
    assert ok and ("POST", "/rest/agile/1.0/sprint/42/issue") in calls


def test_pending_placements_lists_labeled_tickets():
    keys = J.pending_placements("ECO", caller=_agile_caller(pending=["ECO-73", "ECO-80"]))
    assert keys == ["ECO-73", "ECO-80"]


def test_create_default_recommends_but_does_NOT_autoplace(monkeypatch, capsys):
    # THE BEHAVIOR CHANGE: create (no --sprint) → recommendation surfaced + left in backlog labeled
    # pending; NEVER auto-added to the sprint (that's the operator's call).
    monkeypatch.setattr(J, "find_identity", lambda p: None)
    for k in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_TOKEN"):
        monkeypatch.setenv(k, "x")
    monkeypatch.setattr(J, "create_issue", lambda *a, **k: (True, "ECO-90"))
    calls = []
    monkeypatch.setattr(J, "_default_caller", lambda: _agile_caller(active=True, calls=calls))
    assert J.main(["create", "--project", "ECO", "--summary", "work"]) == 0
    out, err = capsys.readouterr()
    assert out.strip() == "ECO-90"                                       # stdout stays scriptable
    assert "recommended placement" in err and "Sprint 9" in err         # recommendation ALWAYS surfaced
    assert "YOURS to decide" in err and J.PENDING_LABEL in err          # operator decides; left pending
    assert ("POST", "/rest/agile/1.0/sprint/42/issue") not in calls     # NOT auto-placed in the sprint
    assert ("POST", "/rest/agile/1.0/backlog/issue") in calls           # conscious backlog
    assert any(m == "PUT" and "/issue/ECO-90" in p for m, p in calls)   # labeled pending


def test_create_explicit_sprint_is_the_operators_decision(monkeypatch, capsys):
    monkeypatch.setattr(J, "find_identity", lambda p: None)
    for k in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_TOKEN"):
        monkeypatch.setenv(k, "x")
    monkeypatch.setattr(J, "create_issue", lambda *a, **k: (True, "ECO-92"))
    calls = []
    monkeypatch.setattr(J, "_default_caller", lambda: _agile_caller(active=True, calls=calls))
    assert J.main(["create", "--project", "ECO", "--summary", "w", "--sprint", "active"]) == 0
    assert ("POST", "/rest/agile/1.0/sprint/42/issue") in calls         # explicit --sprint active → placed
    assert J.PENDING_LABEL not in capsys.readouterr().err               # not pending — the operator chose


def test_create_explicit_backlog_has_no_pending_label(monkeypatch, capsys):
    monkeypatch.setattr(J, "find_identity", lambda p: None)
    for k in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_TOKEN"):
        monkeypatch.setenv(k, "x")
    monkeypatch.setattr(J, "create_issue", lambda *a, **k: (True, "ECO-93"))
    calls = []
    monkeypatch.setattr(J, "_default_caller", lambda: _agile_caller(active=True, calls=calls))
    assert J.main(["create", "--project", "ECO", "--summary", "w", "--sprint", "backlog"]) == 0
    assert ("POST", "/rest/agile/1.0/backlog/issue") in calls
    assert not any(m == "PUT" for m, p in calls)                        # explicit backlog → no pending label


def test_create_on_kanban_skips_placement(monkeypatch, capsys):
    monkeypatch.setattr(J, "find_identity", lambda p: None)
    for k in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_TOKEN"):
        monkeypatch.setenv(k, "x")
    monkeypatch.setattr(J, "create_issue", lambda *a, **k: (True, "ECO-91"))
    calls = []
    monkeypatch.setattr(J, "_default_caller", lambda: _agile_caller(supports=False, calls=calls))
    assert J.main(["create", "--project", "ECO", "--summary", "work"]) == 0
    out, err = capsys.readouterr()
    assert out.strip() == "ECO-91" and "recommended" not in err         # Kanban → N/A, no sprint noise
    assert not any("/sprint/" in p for _, p in calls)
