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
