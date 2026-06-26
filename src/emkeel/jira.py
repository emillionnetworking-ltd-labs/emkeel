"""Jira helpers — transition (post-merge automation) + create (convenience) + existence checks.

The transition is NOT a gate: it runs after a PR merges to close the loop. `create_issue` mirrors
it (POST a new ticket). `issue_status` backs the hard existence check `check_ticket_link` now does.
The HTTP layer is injectable so the decision logic is unit-tested without network.

CLI:  python -m emkeel.jira [KEY] [--status Done]          transition (KEY from EMKEEL_BRANCH/PR_TITLE)
      python -m emkeel.jira create --project ECO --summary "..." [--type Task]
      create makes the issue in the project's INITIAL state — it has no --status (Done is earned by the
      work + the merge, via `transition`, never written at create). Creds: JIRA_BASE_URL / EMAIL / TOKEN.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from emkeel.gates.check_ticket_link import find_ticket_key
from emkeel.isolation import find_identity
from emkeel.lanes import is_dependabot_lane, is_maint_lane


def _isolation_block_project(project: str) -> str | None:
    """Defense in depth (mirrors the PreToolUse guard): refuse a Jira project that isn't THIS repo's
    declared `project_key`, even when the CLI is called directly. None = allowed. Fail-safe: ungoverned
    repo (no emkeel.toml) → no enforcement."""
    ident = find_identity(".")
    if ident and ident.get("project_key") and project and project != ident["project_key"]:
        return (f"emkeel isolation: this repo's Jira project is '{ident['project_key']}', "
                f"refusing to act on project '{project}' (cross-repo).")
    return None


_JIRA_KEYS = ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_TOKEN")


def _scoped_env_values() -> dict[str, str]:
    """Read the SCOPED `.env` of THIS repo (the one beside emkeel.toml) IN-PROCESS — so creds work even
    when `direnv` isn't installed (the `.envrc` never loaded them into the shell). Strictly scoped: only
    this repo's `.env` (via the isolation identity's root), never another repo's. Empty dict on no
    identity / no file / parse error (fail-safe — never raises). Does NOT relax the isolation guard."""
    try:
        ident = find_identity(".")
        if not ident or not ident.get("root"):
            return {}
        envp = Path(ident["root"]) / ".env"
        if not envp.is_file():
            return {}
        out: dict[str, str] = {}
        for ln in envp.read_text(encoding="utf-8", errors="replace").splitlines():
            ln = ln.strip()
            if not ln or ln.startswith("#") or "=" not in ln:
                continue
            k, _, v = ln.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
        return out
    except Exception:
        return {}


def _creds() -> dict[str, str]:
    """The Jira creds, env first, falling back to this repo's scoped `.env` (direnv-independent)."""
    scoped = _scoped_env_values()
    return {k: (os.environ.get(k) or scoped.get(k, "")) for k in _JIRA_KEYS}


def secrets_present() -> bool:
    """True if all the Jira creds are available — from the environment OR this repo's scoped `.env`."""
    return all(_creds().values())


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
    c = _creds()                       # env first, then this repo's scoped .env (direnv-independent)
    return _http_caller(c["JIRA_BASE_URL"], c["JIRA_EMAIL"], c["JIRA_TOKEN"])


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


def issue_created(key: str, *, caller=None) -> tuple[int, str | None]:
    """(http_status, the issue's `created` ISO8601 timestamp) — lets a gate verify a ticket PREDATES the
    work (the `created` field is set by Jira's server, a fact the agent can't backdate)."""
    caller = caller or _default_caller()
    status, data = caller("GET", f"/rest/api/3/issue/{key}?fields=created")
    created = None
    if status == 200 and isinstance(data, dict):
        created = data.get("fields", {}).get("created")
    return status, created


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


# ── sprint placement (KEEL-106/111): no ticket is orphaned in silence; the OPERATOR decides ───────────
# When the project uses sprints, every newly created ticket gets a surfaced recommendation and a CONSCIOUS
# backlog placement — emkeel never auto-adds it to a sprint. The 53-orphan incident (ECO tickets with no
# sprint) came from nothing guiding placement; ECO-73 then slipped because detection missed a Team-managed
# board with sprints. The INVARIANT: a recommendation is ALWAYS produced + surfaced, and the ticket is
# always consciously placed (left in the backlog, labeled pending) — never silence. But the SPRINT placement
# is the OPERATOR's call: by default we recommend + leave it pending, not auto-place. N/A on Kanban.
# Best-effort + non-fatal: the ticket already exists, so a placement hiccup is a loud ::warning::, never a
# create failure — and never a silent orphan.

PENDING_LABEL = "emkeel-placement-pending"


@dataclass(frozen=True)
class Placement:
    """A sprint-placement recommendation/decision. `kind` ∈ {active_sprint, backlog, none, indeterminate}:
    `none` = the project doesn't use sprints (Kanban) → N/A; `indeterminate` = the Agile API couldn't be
    reached to decide (surfaced as a warning, never a silent skip)."""
    kind: str
    rationale: str
    sprint_id: int | None = None
    sprint_name: str | None = None


def _sprint_board(project: str, *, caller) -> tuple[int | None, bool]:
    """(id of a board that SUPPORTS sprints, reachable). Detected by CAPABILITY — a board whose sprint
    endpoint answers 200 — NOT by `type=scrum`, so a Team-managed/'simple' board that HAS sprints (e.g.
    ECO's board 100, which the `type=scrum` filter silently misses) is correctly recognized. A Kanban board
    answers 400 ('does not support sprints') and is skipped. reachable=False ONLY when the boards list
    itself can't be read (→ indeterminate, never a silent Kanban)."""
    status, data = caller("GET", f"/rest/agile/1.0/board?projectKeyOrId={project}")
    if status != 200 or not isinstance(data, dict):
        return None, False
    for b in (data.get("values") or []):
        bid = b.get("id")
        if bid is None:
            continue
        st, _ = caller("GET", f"/rest/agile/1.0/board/{bid}/sprint?maxResults=1")
        if st == 200:                      # the board supports sprints (capability, regardless of type)
            return bid, True
    return None, True                      # boards exist but none supports sprints → genuine Kanban


def _active_sprint(board_id: int, *, caller) -> dict | None:
    status, data = caller("GET", f"/rest/agile/1.0/board/{board_id}/sprint?state=active")
    if status != 200 or not isinstance(data, dict):
        return None
    vals = data.get("values") or []
    return vals[0] if vals else None


def recommend_placement(project: str, *, caller=None) -> Placement:
    """ALWAYS return a placement recommendation (the invariant: never 'no recommendation'): the active
    sprint if one is running (the work has a home), else the backlog. `none` on Kanban; `indeterminate`
    if the Agile API can't be reached."""
    caller = caller or _default_caller()
    board_id, reachable = _sprint_board(project, caller=caller)
    if not reachable:
        return Placement("indeterminate", "couldn't reach the Jira Agile API to check sprint usage")
    if board_id is None:
        return Placement("none", "project has no board that supports sprints (Kanban) — sprints don't apply")
    sprint = _active_sprint(board_id, caller=caller)
    if sprint:
        return Placement("active_sprint", "work is in progress — the active sprint is its home",
                         sprint_id=sprint.get("id"), sprint_name=sprint.get("name"))
    return Placement("backlog", "no active sprint — groom it into a future sprint from the backlog")


def place_issue(key: str, placement: Placement, *, caller=None) -> tuple[bool, str]:
    """Apply a placement. active_sprint → add to the sprint; backlog → move to the backlog CONSCIOUSLY
    (an explicit API call, not a silent no-op); none/indeterminate → nothing to do."""
    caller = caller or _default_caller()
    if placement.kind == "active_sprint":
        st, _ = caller("POST", f"/rest/agile/1.0/sprint/{placement.sprint_id}/issue", {"issues": [key]})
        if st in (200, 204):
            return True, f"{key} placed in sprint '{placement.sprint_name}' (#{placement.sprint_id})"
        return False, f"{key}: could not add to sprint #{placement.sprint_id} (HTTP {st})"
    if placement.kind == "backlog":
        st, _ = caller("POST", "/rest/agile/1.0/backlog/issue", {"issues": [key]})
        if st in (200, 204):
            return True, f"{key} placed in the backlog"
        return False, f"{key}: could not move to the backlog (HTTP {st})"
    return True, f"{key}: no placement ({placement.kind})"


def _resolve_placement(choice: str | None, rec: Placement, project: str, *, caller) -> Placement:
    """Turn an EXPLICIT `--sprint` choice into a concrete placement. 'backlog' / 'active' / a numeric sprint
    id force a specific placement — this is the operator deciding at create time. ('auto'/None is handled by
    the caller as recommend-but-don't-place, so it isn't expected here.)"""
    if choice == "backlog":
        return Placement("backlog", "chosen explicitly (--sprint backlog)")
    if choice == "active":
        if rec.kind == "active_sprint":
            return Placement("active_sprint", "chosen explicitly (--sprint active)",
                             sprint_id=rec.sprint_id, sprint_name=rec.sprint_name)
        board_id, reachable = _sprint_board(project, caller=caller)
        sprint = _active_sprint(board_id, caller=caller) if (reachable and board_id) else None
        if sprint:
            return Placement("active_sprint", "chosen explicitly (--sprint active)",
                             sprint_id=sprint.get("id"), sprint_name=sprint.get("name"))
        return Placement("backlog", "no active sprint to use — fell back to the backlog")
    if str(choice).isdigit():
        return Placement("active_sprint", f"chosen explicitly (--sprint {choice})",
                         sprint_id=int(choice), sprint_name=f"#{choice}")
    return rec


def _mark_pending(key: str, *, caller) -> tuple[bool, str]:
    """Leave the issue CONSCIOUSLY in the backlog and LABEL it pending an operator placement decision —
    so it's surfaced now and discoverable later (`emkeel doctor`), without auto-placing it in a sprint."""
    caller("POST", "/rest/agile/1.0/backlog/issue", {"issues": [key]})        # conscious backlog (best-effort)
    st, _ = caller("PUT", f"/rest/api/3/issue/{key}", {"update": {"labels": [{"add": PENDING_LABEL}]}})
    if st in (200, 204):
        return True, f"left in the backlog, labeled '{PENDING_LABEL}'"
    return False, f"left in the backlog but could not add the '{PENDING_LABEL}' label (HTTP {st})"


def pending_placements(project: str, *, caller=None) -> list[str]:
    """Keys of issues in `project` LABELED pending a sprint-placement decision and not yet Done — the
    `emkeel doctor` nudge: the recommendation was surfaced and the ticket left consciously in the backlog;
    these still await the operator's call. Empty on any API hiccup (best-effort, never raises here)."""
    import urllib.parse
    caller = caller or _default_caller()
    jql = (f"project = {project} AND labels = {PENDING_LABEL} AND statusCategory != Done "
           "ORDER BY created DESC")
    status, data = caller("GET", f"/rest/api/3/search?jql={urllib.parse.quote(jql)}&fields=key&maxResults=50")
    if status != 200 or not isinstance(data, dict):
        return []
    return [i.get("key") for i in (data.get("issues") or []) if i.get("key")]


def _place_after_create(key: str, project: str, choice: str | None) -> None:
    """No-orphan, operator-decides: when the project uses sprints, ALWAYS surface the recommendation. By
    DEFAULT (no `--sprint`) do NOT auto-add to a sprint — leave the ticket in the backlog labeled pending
    for the operator to promote. An explicit `--sprint active|backlog|<id>` is the operator deciding at
    create time. All messaging is on stderr (stdout stays just the key). Non-fatal by design."""
    try:
        caller = _default_caller()
        rec = recommend_placement(project, caller=caller)
        if rec.kind == "none":
            return                                # Kanban — sprints don't apply; nothing to surface
        if rec.kind == "indeterminate":
            print(f"::warning::{key}: {rec.rationale} — place it in a sprint/backlog manually so it isn't "
                  "orphaned.", file=sys.stderr)
            return
        where = (f"sprint '{rec.sprint_name}' (#{rec.sprint_id})" if rec.kind == "active_sprint"
                 else "the backlog")
        print(f"::notice::{key}: recommended placement → {where} ({rec.rationale}).", file=sys.stderr)

        explicit = choice not in (None, "auto")
        # DEFAULT + a sprint is recommended → the OPERATOR decides: leave it pending, never auto-place.
        if not explicit and rec.kind == "active_sprint":
            ok, msg = _mark_pending(key, caller=caller)
            tail = "" if ok else " — do it manually so it isn't orphaned"
            print(f"::notice::{key}: placement is YOURS to decide — {msg}; promote it to sprint "
                  f"'{rec.sprint_name}' (#{rec.sprint_id}) when you choose (`emkeel doctor` lists pending "
                  f"ones).{tail}", file=sys.stderr)
            return
        # No active sprint (rec=backlog) or an explicit choice → apply the concrete placement.
        target = rec if not explicit else _resolve_placement(choice, rec, project, caller=caller)
        ok, msg = place_issue(key, target, caller=caller)
        print((msg if ok else f"::warning::{msg} — place it manually so it isn't orphaned."),
              file=sys.stderr)
    except Exception as e:                        # never break the agent flow over a placement hiccup…
        print(f"::warning::{key}: sprint placement skipped ({e}) — place it manually so it isn't orphaned.",
              file=sys.stderr)                     # …but never silent either.


def create_and_place(project: str, summary: str, issuetype: str = "Task", description: str = "",
                     sprint: str = "auto") -> tuple[int, str | None]:
    """The shared create core of `emkeel jira create` AND `emkeel start` — both create the SAME way (same
    isolation/creds guards, same no-orphan sprint placement). Returns (exit_code, new_key | None). HARD,
    non-silent failures: on a block or missing creds it errors RED and returns (1, None) — the caller must
    NOT proceed to open a PR with no ticket."""
    blocked = _isolation_block_project(project)
    if blocked:
        print(f"::error::{blocked}\nSTOP: do not open a PR without a ticket — fix the project/window first.",
              file=sys.stderr)
        return 1, None
    if not secrets_present():
        print("::error::Cannot create a Jira issue — no Jira creds in the environment or this repo's "
              "scoped .env (JIRA_BASE_URL / JIRA_EMAIL / JIRA_TOKEN). Run `emkeel connect`.\n"
              "STOP: do not open a PR without a ticket.", file=sys.stderr)
        return 1, None
    ok, res = create_issue(project, summary, issuetype, description)
    if not ok:
        print(f"::error::{res}", file=sys.stderr)
        return 1, None
    _place_after_create(res, project, sprint)    # no-orphan: always recommend + place when sprints used
    return 0, res


def _main_create(rest: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="emkeel jira create", description="Create a Jira issue.")
    ap.add_argument("--project", required=True, help="project key, e.g. ECO")
    ap.add_argument("--summary", required=True)
    ap.add_argument("--type", dest="issuetype", default="Task")
    ap.add_argument("--description", default="")
    ap.add_argument("--sprint", default="auto",
                    help="sprint placement when the project uses sprints: auto (default = recommend, then "
                         "leave it in the backlog pending YOUR decision) | active | backlog | <sprintId>")
    # `--status` is intentionally still PARSED so a born-Done attempt gets a clear message instead of
    # argparse's opaque "unrecognized arguments" — it is rejected below, never honored.
    ap.add_argument("--status", default=None, help=argparse.SUPPRESS)
    ns = ap.parse_args(rest)
    # A ticket is BORN in the project's INITIAL state — creation never sets status. `Done` (and any other
    # status) is EARNED by the work + the merge, not auto-written at create — the spirit of KEEL-104 applied
    # to completion (ECO-69/70 were created already Done, skipping work→merge→Done). Reject BEFORE creating
    # so nothing is half-made; a status change goes through `emkeel jira transition` + the merge.
    if ns.status is not None:
        print("::error::`emkeel jira create` does not set status — a ticket is born in the project's "
              "INITIAL state. A terminal status (Done/Closed/Resolved/…) is earned by the work and the "
              "merge, never written at create. Drop --status; move the issue later with "
              "`emkeel jira transition` once the work merges.\nSTOP: re-run create without --status.",
              file=sys.stderr)
        return 1
    code, key = create_and_place(ns.project, ns.summary, ns.issuetype, ns.description, ns.sprint)
    if key:
        print(key)                               # the new key (stdout, scriptable) — in the initial state
    return code


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
    if is_dependabot_lane(branch):
        # Same for the Dependabot lane — bot PRs carry no ticket, so there's nothing to transition.
        print("OK: dependabot lane — no ticket to transition.")
        return 0
    key = ns.key or find_ticket_key(branch, os.environ.get("EMKEEL_PR_TITLE", ""))
    if key:
        blocked = _isolation_block_project(key.split("-")[0])
        if blocked:
            print(f"::error::{blocked}", file=sys.stderr)
            return 1
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
