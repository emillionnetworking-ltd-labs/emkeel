"""check_ticket_precedes_work — the ticket must be created BEFORE the branch's first commit (ticket-first)."""

import emkeel.gates.check_ticket_precedes_work as g
import emkeel.jira as jira


def _run(monkeypatch, *, branch="feat/KEEL-1-x", pr_title="",
         created="2026-06-26T10:00:00+00:00", first="2026-06-26T10:05:00+00:00",
         status=200, secrets=True):
    monkeypatch.setenv("EMKEEL_BRANCH", branch)
    monkeypatch.setenv("EMKEEL_PR_TITLE", pr_title)
    monkeypatch.setenv("EMKEEL_BASE_REF", "main")
    monkeypatch.setattr(jira, "secrets_present", lambda: secrets)
    monkeypatch.setattr(jira, "issue_created", lambda key, **k: (status, created))
    monkeypatch.setattr(g, "first_commit_date", lambda base, **k: g._parse_iso(first))
    return g.main()


def test_ticket_before_first_commit_passes(monkeypatch):
    assert _run(monkeypatch, created="2026-06-26T10:00:00+00:00", first="2026-06-26T10:05:00+00:00") == 0


def test_ticket_after_first_commit_fails(monkeypatch, capsys):
    # the KEEL-115 anti-pattern: code committed, THEN the ticket created → FAIL.
    assert _run(monkeypatch, created="2026-06-26T10:30:00+00:00", first="2026-06-26T10:00:00+00:00") == 1
    assert "after the work" in capsys.readouterr().err.lower()


def test_within_skew_tolerance_passes(monkeypatch):
    # ticket created 2 min after the commit (clock skew) → within the 3-min tolerance → OK.
    assert _run(monkeypatch, created="2026-06-26T10:02:00+00:00", first="2026-06-26T10:00:00+00:00") == 0


def test_just_past_skew_tolerance_fails(monkeypatch):
    # 4 min after → past the 3-min tolerance → FAIL.
    assert _run(monkeypatch, created="2026-06-26T10:04:00+00:00", first="2026-06-26T10:00:00+00:00") == 1


def test_maint_lane_is_na(monkeypatch):
    assert _run(monkeypatch, branch="emkeel-maint/refresh") == 0


def test_dependabot_lane_is_na(monkeypatch):
    assert _run(monkeypatch, branch="dependabot/pip/x") == 0


def test_no_key_is_na(monkeypatch):
    # missing key is check_ticket_link's FAIL to own, not this gate's.
    assert _run(monkeypatch, branch="feat/no-key-here", pr_title="") == 0


def test_no_secrets_is_inconclusive(monkeypatch):
    assert _run(monkeypatch, secrets=False, created="2026-06-26T11:00:00+00:00",
                first="2026-06-26T10:00:00+00:00") == 0          # would FAIL if checked; skipped w/o secrets


def test_jira_error_is_inconclusive(monkeypatch):
    assert _run(monkeypatch, status=500, created=None) == 0      # Jira hiccup never blocks a merge


def test_no_first_commit_is_inconclusive(monkeypatch):
    monkeypatch.setattr(g, "first_commit_date", lambda base, **k: None)
    monkeypatch.setenv("EMKEEL_BRANCH", "feat/KEEL-1-x")
    monkeypatch.setenv("EMKEEL_BASE_REF", "main")
    monkeypatch.setattr(jira, "secrets_present", lambda: True)
    monkeypatch.setattr(jira, "issue_created", lambda key, **k: (200, "2026-06-26T10:00:00+00:00"))
    assert g.main() == 0
