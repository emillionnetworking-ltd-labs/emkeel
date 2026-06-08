"""Transition a Jira issue (e.g., to Done) — the post-merge automation.

NOT a gate: runs after a PR merges to close the loop, and is non-blocking. The HTTP
layer is injectable so the decision logic is unit-tested without network.

CLI:  python -m emkeel.jira [KEY] [--status Done]
      KEY defaults to the ticket key found in EMKEEL_BRANCH / EMKEEL_PR_TITLE.
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


def transition_issue(key: str, target: str = "Done", *, caller=None) -> tuple[bool, str]:
    """Move ``key`` to ``target``. Returns (ok, message).

    Soft-success if the target transition isn't available (most often: already there),
    so this post-merge automation never goes noisily red for a benign reason.
    """
    if caller is None:
        caller = _http_caller(
            os.environ.get("JIRA_BASE_URL", ""),
            os.environ.get("JIRA_EMAIL", ""),
            os.environ.get("JIRA_TOKEN", ""),
        )
    status, data = caller("GET", f"/rest/api/3/issue/{key}/transitions")
    if status != 200:
        return False, f"{key}: cannot read transitions (HTTP {status})"
    tid = pick_transition(data.get("transitions", []), target)
    if tid is None:
        return True, f"{key}: '{target}' not available (already {target}?) — skipped"
    status, _ = caller("POST", f"/rest/api/3/issue/{key}/transitions", {"transition": {"id": tid}})
    if status == 204:
        return True, f"{key} -> {target}"
    return False, f"{key}: transition POST failed (HTTP {status})"


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    ap = argparse.ArgumentParser(prog="emkeel.jira", description="Transition a Jira issue.")
    ap.add_argument("key", nargs="?", default=None, help="ticket key (default: from EMKEEL_BRANCH/PR_TITLE)")
    ap.add_argument("--status", default="Done")
    ns = ap.parse_args(argv)
    key = ns.key or find_ticket_key(
        os.environ.get("EMKEEL_BRANCH", ""), os.environ.get("EMKEEL_PR_TITLE", "")
    )
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
    print(msg, file=(sys.stdout if ok else sys.stderr))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
