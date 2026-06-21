"""Tests for emkeel doctor (the pure report logic)."""

from emkeel.doctor import report_lines


def _has(lines, sub):
    return any(sub in ln for ln in lines)


def test_not_governed():
    r = report_lines({"governed": False, "connected": False})
    assert _has(r, "✗") and _has(r, "emkeel setup")


def test_not_connected_says_create_and_push():
    r = report_lines({"governed": True, "connected": False})
    assert _has(r, "not connected to GitHub") and _has(r, "gh repo create")
    # doesn't claim anything about secrets when there's no repo yet
    assert not _has(r, "Jira secrets")


def test_connected_but_no_gh():
    r = report_lines({"governed": True, "connected": True, "repo": "a/b", "gh_ok": False})
    assert _has(r, "gh auth login")


def test_all_good():
    r = report_lines({"governed": True, "connected": True, "repo": "a/b",
                      "gh_ok": True, "secrets_ok": True, "protection_ok": True})
    assert _has(r, "All set")


def test_pending_lists_gaps_with_links():
    r = report_lines({"governed": True, "connected": True, "repo": "a/b",
                      "gh_ok": True, "secrets_ok": False, "protection_ok": False})
    assert _has(r, "Jira secrets") and _has(r, "a/b/settings/secrets/actions/new")
    assert _has(r, "gates") and _has(r, "a/b/settings/branches")
    assert _has(r, "pending")


from types import SimpleNamespace
from emkeel.doctor import _required_contexts


def _fake_run(classic_rc, classic_out, rules_rc, rules_out):
    # gh --jq streams one context per line; mocks mirror that (newline-separated, not a JSON array).
    def run(args):
        joined = " ".join(args)
        if "/protection" in joined:
            return SimpleNamespace(returncode=classic_rc, stdout=classic_out)
        return SimpleNamespace(returncode=rules_rc, stdout=rules_out)
    return run


def test_required_contexts_via_classic():
    # AC5 (classic path): contexts come from classic protection.
    got = _required_contexts("a/b", "main", run=_fake_run(0, "gates\nSecurity Gate (All Checks)\n", 0, ""))
    assert got == {"gates", "Security Gate (All Checks)"}


def test_required_contexts_via_ruleset():
    # AC5 (ruleset path): classic 404 (rc!=0); the ruleset endpoint streams the contexts.
    got = _required_contexts("a/b", "main", run=_fake_run(1, '{"message":"Branch not protected"}', 0, "gates\n"))
    assert got == {"gates"}


def test_required_contexts_union_of_both():
    got = _required_contexts("a/b", "main", run=_fake_run(0, "gates\n", 0, "Security Gate (All Checks)\n"))
    assert got == {"gates", "Security Gate (All Checks)"}


def test_required_contexts_neither_enforced():
    assert _required_contexts("a/b", "main", run=_fake_run(0, "", 0, "")) == set()


def test_required_contexts_indeterminate_is_none():
    # AC6: both API calls error → None (caller shows '?'), never a crash.
    assert _required_contexts("a/b", "main", run=_fake_run(1, "boom", 1, "boom")) is None


# ── report: declared required_checks enforcement (AC1/AC2/AC3/AC4) ──────────────

_BASE = {"governed": True, "connected": True, "repo": "a/b", "gh_ok": True,
         "secrets_ok": True, "default_branch": "main"}


def test_all_required_enforced_is_ok():
    # AC1: gates + an extra declared check, all enforced → OK, lists the extras.
    r = report_lines({**_BASE, "protection_ok": True,
                      "required_checks": ["gates", "Security Gate (All Checks)"], "required_missing": []})
    assert _has(r, "All set")
    assert _has(r, "required checks enforced: Security Gate (All Checks)")


def test_declared_check_not_enforced_reports_drift_with_fix():
    # AC2: a declared check missing → drift line + the exact gh api fix command.
    r = report_lines({**_BASE, "protection_ok": True,
                      "required_checks": ["gates", "Security Gate (All Checks)"],
                      "required_missing": ["Security Gate (All Checks)"]})
    assert _has(r, "required check 'Security Gate (All Checks)' declared but NOT enforced")
    assert _has(r, "gh api -X POST repos/a/b/branches/main/protection/required_status_checks/contexts")
    assert _has(r, "contexts[]=Security Gate (All Checks)")
    assert _has(r, "pending")


def test_no_required_checks_key_is_backward_compatible():
    # AC3/AC4: no required_checks declared → only the 'gates' line, no extra block, no false drift.
    r = report_lines({**_BASE, "protection_ok": True})
    assert _has(r, "'gates' check required") and _has(r, "All set")
    assert not _has(r, "declared but NOT enforced")


def test_gates_always_checked_even_if_not_listed():
    # AC4: gates missing → its own ✗ line (it's always required), regardless of the declared list.
    r = report_lines({**_BASE, "protection_ok": False, "required_checks": ["Security Gate (All Checks)"],
                      "required_missing": ["gates"]})
    assert _has(r, "'gates' check required") and _has(r, "a/b/settings/branches")


def test_indeterminate_protection_shows_question_mark():
    # AC6: protection unreadable → '?' line, doesn't crash or claim 'enforced'.
    r = report_lines({**_BASE, "protection_ok": None, "required_missing": []})
    assert _has(r, "? 'gates' check required") and _has(r, "couldn't read branch protection")


# ── gather: end-to-end with gh/git mocked, driving the declared-vs-enforced computation ─

import emkeel.doctor as doctor
from emkeel.init import Config, apply


def _gather_run(enforced_lines):
    """Fake the git/gh subprocess layer doctor.gather uses; protection returns `enforced_lines`."""
    def run(args):
        j = " ".join(args)
        if "remote get-url origin" in j:
            return SimpleNamespace(returncode=0, stdout="git@github.com:a/b.git\n")
        if "branch --show-current" in j:
            return SimpleNamespace(returncode=0, stdout="feat/KEEL-82-x\n")
        if "auth status" in j:
            return SimpleNamespace(returncode=0, stdout="ok")
        if "--jq .default_branch" in j:
            return SimpleNamespace(returncode=0, stdout="main\n")
        if "secret list" in j:
            return SimpleNamespace(returncode=0, stdout="JIRA_BASE_URL\nJIRA_EMAIL\nJIRA_TOKEN\n")
        if "/protection" in j:
            return SimpleNamespace(returncode=0, stdout=enforced_lines)
        if "/rules/branches" in j:
            return SimpleNamespace(returncode=0, stdout="")
        return SimpleNamespace(returncode=1, stdout="")
    return run


def _governed_repo(tmp_path, required_checks):
    apply(tmp_path, Config(jira_url="https://x.atlassian.net", jira_project="DEMO", github_repo="a/b"),
          force=False, dry_run=False)
    toml = (tmp_path / "emkeel.toml").read_text()
    decl = ", ".join(f'"{c}"' for c in required_checks)
    toml = toml.replace('repo = "a/b"\n', f'repo = "a/b"\nrequired_checks = [{decl}]\n')
    (tmp_path / "emkeel.toml").write_text(toml)


def test_gather_all_enforced(tmp_path, monkeypatch):
    _governed_repo(tmp_path, ["gates", "Security Gate (All Checks)"])
    monkeypatch.setattr(doctor, "_run", _gather_run("gates\nSecurity Gate (All Checks)\n"))
    st = doctor.gather(tmp_path)
    assert st["protection_ok"] is True and st["required_missing"] == []
    assert _has(report_lines(st), "required checks enforced: Security Gate (All Checks)")


def test_gather_declared_check_missing(tmp_path, monkeypatch):
    _governed_repo(tmp_path, ["gates", "Security Gate (All Checks)"])
    monkeypatch.setattr(doctor, "_run", _gather_run("gates\n"))    # security check NOT enforced
    st = doctor.gather(tmp_path)
    assert st["required_missing"] == ["Security Gate (All Checks)"]
    assert _has(report_lines(st), "declared but NOT enforced")


def test_gather_detects_inflight_pr_when_drifting(tmp_path, monkeypatch):
    _governed_repo(tmp_path, ["gates"])
    monkeypatch.setattr("emkeel.update.wiring_drift", lambda target: ["AGENTS.md"])   # force drift

    def run(args):
        j = " ".join(args)
        if "remote get-url origin" in j:
            return SimpleNamespace(returncode=0, stdout="git@github.com:a/b.git\n")
        if "auth status" in j:
            return SimpleNamespace(returncode=0, stdout="ok")
        if "pr list" in j:
            return SimpleNamespace(returncode=0, stdout='[{"number": 99, "headRefName": "emkeel-maint/0.1.69-z"}]')
        return SimpleNamespace(returncode=1, stdout="")        # everything else (incl. protection) errors
    monkeypatch.setattr(doctor, "_run", run)
    st = doctor.gather(tmp_path)
    assert st["maint_pr"] == 99
    assert _has(report_lines(st), "refresh in flight (PR #99)")


def test_gather_inflight_degrades_when_gh_pr_list_fails(tmp_path, monkeypatch):
    _governed_repo(tmp_path, ["gates"])
    monkeypatch.setattr("emkeel.update.wiring_drift", lambda target: ["AGENTS.md"])

    def run(args):
        j = " ".join(args)
        if "remote get-url origin" in j:
            return SimpleNamespace(returncode=0, stdout="git@github.com:a/b.git\n")
        if "auth status" in j:
            return SimpleNamespace(returncode=0, stdout="ok")
        return SimpleNamespace(returncode=1, stdout="")        # gh pr list fails too → degrade
    monkeypatch.setattr(doctor, "_run", run)
    st = doctor.gather(tmp_path)
    assert st["maint_pr"] is None
    assert _has(report_lines(st), "run: emkeel update")        # falls back to the normal nudge


def test_gather_not_connected_returns_early(tmp_path):
    # governed repo with no git remote → connected False, no gh calls attempted.
    _governed_repo(tmp_path, ["gates"])
    st = doctor.gather(tmp_path)
    assert st["governed"] is True and st["connected"] is False


def test_run_executes_a_command():
    r = doctor._run(["echo", "hi"])
    assert r.returncode == 0 and "hi" in r.stdout


def test_gather_gh_ok_but_apis_fail_is_graceful(tmp_path, monkeypatch):
    # connected + gh authed, but default-branch lookup, secret list, and protection all error:
    # secrets_ok stays None, default branch stays 'main', protection unreadable → None ('?').
    _governed_repo(tmp_path, ["gates"])

    def run(args):
        j = " ".join(args)
        if "remote get-url origin" in j:
            return SimpleNamespace(returncode=0, stdout="git@github.com:a/b.git\n")
        if "auth status" in j:
            return SimpleNamespace(returncode=0, stdout="ok")
        return SimpleNamespace(returncode=1, stdout="")     # everything else errors
    monkeypatch.setattr(doctor, "_run", run)
    st = doctor.gather(tmp_path)
    assert st["connected"] is True and st["gh_ok"] is True
    assert st["secrets_ok"] is None and st["default_branch"] == "main"
    assert st["protection_ok"] is None       # indeterminate → '?' in the report
    assert _has(report_lines(st), "couldn't read branch protection")


def test_main_prints_report(monkeypatch, capsys):
    monkeypatch.setattr(doctor, "gather", lambda target: {**_BASE, "protection_ok": True})
    assert doctor.main() == 0
    assert "emkeel doctor" in capsys.readouterr().out


def test_stale_wiring_nudges_update():
    r = report_lines({"governed": True, "connected": True, "repo": "a/b", "gh_ok": True,
                      "secrets_ok": True, "protection_ok": True, "drift": ["AGENTS.md"]})
    assert _has(r, "emkeel update") and _has(r, "out of date")


def test_current_wiring_no_nudge():
    r = report_lines({"governed": True, "connected": True, "repo": "a/b", "gh_ok": True,
                      "secrets_ok": True, "protection_ok": True, "drift": []})
    assert not _has(r, "emkeel update")


# ── scoped local credential gap (KEEL-93) ──────────────────────────────────────

def test_doctor_flags_missing_scoped_env():
    r = report_lines({"governed": True, "connected": True, "repo": "a/b", "gh_ok": True,
                      "secrets_ok": True, "protection_ok": True, "drift": [], "env_scoped_ok": False})
    assert _has(r, "scoped local credential") and _has(r, "emkeel connect")
    assert _has(r, "credencial local")                       # bilingual


def test_doctor_silent_when_scoped_env_present():
    r = report_lines({"governed": True, "connected": True, "repo": "a/b", "gh_ok": True,
                      "secrets_ok": True, "protection_ok": True, "drift": [], "env_scoped_ok": True})
    assert not _has(r, "scoped local credential")


# ── wiring_nudge (KEEL-94): cheap local hint ──────────────────────────────────

def test_wiring_nudge_none_when_ungoverned(tmp_path):
    from emkeel.doctor import wiring_nudge
    assert wiring_nudge(tmp_path) is None                  # no emkeel.toml → nothing to nudge


def test_wiring_nudge_flags_stale_stamp_and_missing_cred(tmp_path):
    from emkeel.doctor import wiring_nudge
    (tmp_path / "emkeel.toml").write_text('[emkeel]\ngenerated_with = "0.0.1"\n')   # behind the CLI
    msg = wiring_nudge(tmp_path)
    assert msg and "emkeel update" in msg and "emkeel connect" in msg   # both pending, bilingual


def test_wiring_nudge_clean_when_current(tmp_path, monkeypatch):
    from emkeel import __version__
    from emkeel.doctor import wiring_nudge
    (tmp_path / "emkeel.toml").write_text(f'[emkeel]\ngenerated_with = "{__version__}"\n')
    (tmp_path / ".env").write_text("GH_TOKEN=github_pat_x\n")
    monkeypatch.setattr("emkeel.update.wiring_drift", lambda target: [])    # no drift either
    assert wiring_nudge(tmp_path) is None                  # up to date + cred present → silent


# ── "All set ✓" must not contradict a ⚠ (KEEL-95) ──────────────────────────────

_BASE_OK = {"governed": True, "connected": True, "repo": "a/b", "gh_ok": True,
            "secrets_ok": True, "protection_ok": True}


def test_not_all_set_when_drift_present():
    r = report_lines({**_BASE_OK, "drift": ["AGENTS.md"]})
    assert _has(r, "out of date") and _has(r, "pending") and not _has(r, "All set")


def test_not_all_set_when_scoped_env_missing():
    r = report_lines({**_BASE_OK, "drift": [], "env_scoped_ok": False})
    assert _has(r, "scoped local credential") and _has(r, "pending") and not _has(r, "All set")


def test_all_set_when_truly_clean():
    r = report_lines({**_BASE_OK, "drift": [], "env_scoped_ok": True})
    assert _has(r, "All set")                              # no ⚠ → honest "All set ✓"


def test_gather_detects_scoped_env(tmp_path, monkeypatch):
    import emkeel.doctor as doctor
    from emkeel.init import Config, apply
    apply(tmp_path, Config(github_repo="a/b"), force=False, dry_run=False)
    monkeypatch.setattr("emkeel.update.wiring_drift", lambda target: [])
    assert doctor.gather(tmp_path)["env_scoped_ok"] is False    # no .env yet
    (tmp_path / ".env").write_text("GH_TOKEN=github_pat_x\n")
    assert doctor.gather(tmp_path)["env_scoped_ok"] is True


def test_drift_with_inflight_pr_points_to_pr_not_rerun(monkeypatch):
    # KEEL-84: a refresh already in flight → don't nag 'run: emkeel update'.
    r = report_lines({"governed": True, "connected": True, "repo": "a/b", "gh_ok": True,
                      "secrets_ok": True, "protection_ok": True, "drift": ["AGENTS.md"], "maint_pr": 42})
    assert _has(r, "refresh in flight (PR #42)") and _has(r, "git pull")
    assert not _has(r, "→ run: emkeel update")


def test_drift_without_inflight_pr_says_run_update():
    r = report_lines({"governed": True, "connected": True, "repo": "a/b", "gh_ok": True,
                      "secrets_ok": True, "protection_ok": True, "drift": ["AGENTS.md"], "maint_pr": None})
    assert _has(r, "out of date") and _has(r, "run: emkeel update")


def test_project_mismatch_warns():
    r = report_lines({"governed": True, "connected": True, "repo": "a/b", "gh_ok": True,
                      "secrets_ok": True, "protection_ok": True,
                      "jira_project": "SCRUM", "branch_key": "ECO-1"})
    assert _has(r, "ECO-1") and _has(r, "SCRUM")


def test_project_match_no_warn():
    r = report_lines({"governed": True, "connected": True, "repo": "a/b", "gh_ok": True,
                      "secrets_ok": True, "protection_ok": True,
                      "jira_project": "SCRUM", "branch_key": "SCRUM-9"})
    assert not _has(r, "configured Jira project")
