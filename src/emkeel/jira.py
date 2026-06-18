"""Jira helpers — transition (post-merge automation) + create (convenience) + existence checks.

The transition is NOT a gate: it runs after a PR merges to close the loop. `create_issue` mirrors
it (POST a new ticket). `issue_status` backs the hard existence check `check_ticket_link` now does.
The HTTP layer is injectable so the decision logic is unit-tested without network.

CLI:  python -m emkeel.jira [KEY] [--status Done]          transition (KEY from EMKEEL_BRANCH/PR_TITLE)
      python -m emkeel.jira create --project ECO --summary "..." [--type Task] [--status Done]
      Credentials come from JIRA_BASE_URL / JIRA_EMAIL / JIRA_TOKEN.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request

from emkeel.gates.check_ticket_link import find_ticket_key
from emkeel.lanes import is_maint_lane


def secrets_present() -> bool:
    """True if all the Jira secrets needed for the transition are set."""
    return all(os.environ.get(k) for k in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_TOKEN"))


def pick_transition(transitions: list[dict], target: str) -> str | None:
    """Return the id of the transition whose name matches target (case-insensitive)."""
    for t in transitions:
        if str(t.get("name", "")).strip().lower() == target.strip().lower():
            return t.get("id")
    return None


def _http_caller(base_url: str, email: str, token: str):
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()

    def call(method: str, path: str, body=None):
        req = urllib.request.Request(
            f"{base_url.rstrip('/')}{path}",
            data=(json.dumps(body).encode() if body is not None else None),
            method=method,
        )
        req.add_header("Authorization", f"Basic {auth}")
        req.add_header("Accept", "application/json")
        if body is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req) as r:
                text = r.read().decode()
                return r.status, (json.loads(text) if text else {})
        except urllib.error.HTTPError as e:
            return e.code, {"error": e.read().decode()[:200]}

    return call


def _default_caller():
    return _http_caller(
        os.environ.get("JIRA_BASE_URL", ""),
        os.environ.get("JIRA_EMAIL", ""),
        os.environ.get("JIRA_TOKEN", ""),
    )


def issue_status(key: str, *, caller=None) -> int:
    """HTTP status of GET issue/{key}: 200 = exists, 404 = missing, other = indeterminate."""
    caller = caller or _default_caller()
    status, _ = caller("GET", f"/rest/api/3/issue/{key}?fields=status")
    return status


def issue_status_name(key: str, *, caller=None) -> tuple[int, str | None]:
    """(http_status, current status name) — used to VERIFY a transition actually landed."""
    caller = caller or _default_caller()
    status, data = caller("GET", f"/rest/api/3/issue/{key}?fields=status")
    name = None
    if status == 200 and isinstance(data, dict):
        name = data.get("fields", {}).get("status", {}).get("name")
    return status, name


def create_issue(project: str, summary: str, issuetype: str = "Task",
                 description: str = "", *, caller=None) -> tuple[bool, str]:
    """POST a new issue. Returns (True, new_key) on success, (False, message) on failure.

    Mirror of transition_issue — the convenience that lets a flow CREATE a ticket if one is missing
    (the gate is still the hard line; this just makes satisfying it a one-liner)."""
    caller = caller or _default_caller()
    fields = {"project": {"key": project}, "summary": summary, "issuetype": {"name": issuetype}}
    if description:
        fields["description"] = {"type": "doc", "version": 1,
                                 "content": [{"type": "paragraph",
                                              "content": [{"type": "text", "text": description}]}]}
    status, data = caller("POST", "/rest/api/3/issue", {"fields": fields})
    if status == 201 and isinstance(data, dict) and data.get("key"):
        return True, data["key"]
    return False, f"create failed (HTTP {status}): {str(data)[:200]}"


def transition_issue(key: str, target: str = "Done", *, caller=None, verify: bool = True) -> tuple[bool, str]:
    """Move ``key`` to ``target`` and VERIFY it landed. Returns (ok, message).

    The benign soft-success ("already there") is no longer assumed — it is CONFIRMED by reading the
    issue's status back. A 404, a failed POST, or a post-transition status that isn't ``target`` are
    real failures and surface (ok=False) instead of being swallowed.
    """
    caller = caller or _default_caller()

    def _verify_now(skipped: bool) -> tuple[bool, str]:
        if not verify:
            return True, f"{key} -> {target}" if not skipped else f"{key}: '{target}' not available — skipped"
        st, name = issue_status_name(key, caller=caller)
        if st == 200 and name and name.strip().lower() == target.strip().lower():
            tag = "already" if skipped else "->"
            return True, f"{key} {tag} {target} (verified)"
        if skipped:
            return False, f"{key}: '{target}' not available and status is {name!r}, not {target} (HTTP {st})"
        return False, f"{key}: transition POSTed but status is {name!r}, not {target} (HTTP {st})"

    status, data = caller("GET", f"/rest/api/3/issue/{key}/transitions")
    if status == 404:
        return False, f"{key}: issue not found (HTTP 404)"
    if status != 200:
        return False, f"{key}: cannot read transitions (HTTP {status})"
    tid = pick_transition(data.get("transitions", []), target)
    if tid is None:
        return _verify_now(skipped=True)          # target not offered → maybe already there; confirm it
    status, _ = caller("POST", f"/rest/api/3/issue/{key}/transitions", {"transition": {"id": tid}})
    if status != 204:
        return False, f"{key}: transition POST failed (HTTP {status})"
    return _verify_now(skipped=False)


def _main_create(rest: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="emkeel jira create", description="Create a Jira issue.")
    ap.add_argument("--project", required=True, help="project key, e.g. ECO")
    ap.add_argument("--summary", required=True)
    ap.add_argument("--type", dest="issuetype", default="Task")
    ap.add_argument("--description", default="")
    ap.add_argument("--status", default=None, help="optionally transition the new issue to this status")
    ns = ap.parse_args(rest)
    if not secrets_present():
        print("::error::Cannot create a Jira issue — JIRA_BASE_URL / JIRA_EMAIL / JIRA_TOKEN not set.",
              file=sys.stderr)
        return 1
    ok, res = create_issue(ns.project, ns.summary, ns.issuetype, ns.description)
    if not ok:
        print(f"::error::{res}", file=sys.stderr)
        return 1
    print(res)                                   # the new key (stdout, scriptable)
    if ns.status:
        tok, msg = transition_issue(res, ns.status)
        print(msg, file=(sys.stdout if tok else sys.stderr))
        return 0 if tok else 1
    return 0


def _main_transition(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="emkeel.jira", description="Transition a Jira issue.")
    ap.add_argument("key", nargs="?", default=None, help="ticket key (default: from EMKEEL_BRANCH/PR_TITLE)")
    ap.add_argument("--status", default="Done")
    ns = ap.parse_args(argv)
    branch = os.environ.get("EMKEEL_BRANCH", "")
    if is_maint_lane(branch):
        # The scope-gated maintenance lane carries no Jira ticket (check_ticket_link exempts it too) —
        # there's nothing to transition, so SKIP instead of failing on "no ticket key".
        print("OK: emkeel maintenance lane — no ticket to transition.")
        return 0
    key = ns.key or find_ticket_key(branch, os.environ.get("EMKEEL_PR_TITLE", ""))
    if not key:
        print("no ticket key (set EMKEEL_BRANCH/EMKEEL_PR_TITLE or pass KEY)", file=sys.stderr)
        return 1
    if not secrets_present():
        repo = os.environ.get("GITHUB_REPOSITORY", "OWNER/REPO")
        print(f"::warning::Emkeel auto-close is OFF — Jira secrets not set. Add "
              f"JIRA_BASE_URL / JIRA_EMAIL / JIRA_TOKEN at "
              f"https://github.com/{repo}/settings/secrets/actions/new")
        print(f"Skipping Jira transition for {key} (secrets missing).")
        return 0  # non-blocking: don't fail the merge over a missing optional setup step
    ok, msg = transition_issue(key, ns.status)
    # Real failures are VISIBLE now (the workflow no longer swallows them with continue-on-error).
    print((msg if ok else f"::error::{msg}"), file=(sys.stdout if ok else sys.stderr))
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if argv and argv[0] == "create":
        return _main_create(argv[1:])
    return _main_transition(argv)


if __name__ == "__main__":
    sys.exit(main())
