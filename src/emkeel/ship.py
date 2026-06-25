"""Auto-ship emkeel-managed changes through a scope-gated maintenance lane — in an ISOLATED worktree.

Used by `emkeel update` / `emkeel set` (ship-by-default; `--no-ship` opts out). The change is made in
a throwaway `git worktree` checked out at `origin/<default>`, committed, pushed as
`emkeel-maint/<version>-<sha>`, opened as a PR and auto-merged — so it goes through the gates but
NEVER touches your working tree (your in-progress product work is left completely alone).

The `check_ticket_link` gate accepts `emkeel-maint/*` without a Jira ticket because `check_maint_scope`
proves the PR touches nothing but emkeel-managed files — a bounded, self-policing exemption.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from emkeel import connect
from emkeel.lanes import MAINT_PREFIX  # single source of truth (re-exported for back-compat)
from emkeel.update import load_cfg


def inflight_maint_pr(repo: str, run=connect._run) -> int | None:
    """Number of an OPEN PR whose head is an `emkeel-maint/*` lane (a refresh already in flight), or None.

    Pure + injectable (gh boundary passed in) so it's testable without network. Degrades to None when gh
    is unavailable or errors — callers then fall back to normal behavior (ship / 'run: emkeel update')."""
    if not repo:
        return None
    r = run(["gh", "pr", "list", "-R", repo, "--state", "open",
             "--json", "number,headRefName", "--limit", "50"])
    if r.returncode != 0 or not (r.stdout or "").strip():
        return None
    try:
        prs = json.loads(r.stdout)
    except (ValueError, TypeError):
        return None
    for pr in prs:
        if str(pr.get("headRefName", "")).startswith(MAINT_PREFIX):
            return pr.get("number")
    return None


# A check is "bad" (the PR is stuck on it) when its conclusion/state is one of these.
_BAD_CHECK = {"FAILURE", "CANCELLED", "TIMED_OUT", "STARTUP_FAILURE", "ACTION_REQUIRED", "ERROR"}


def maint_pr_status(repo: str, number: int, run=connect._run) -> dict:
    """Health of an in-flight maint PR: {"health": ..., "branch": ...}.

    health ∈ {"failing","behind","healthy","unknown"}. Injectable gh boundary; degrades to "unknown"
    (→ callers just wait, never act blindly) when gh can't tell us."""
    r = run(["gh", "pr", "view", str(number), "-R", repo,
             "--json", "headRefName,mergeStateStatus,statusCheckRollup"])
    if r.returncode != 0 or not (r.stdout or "").strip():
        return {"health": "unknown", "branch": ""}
    try:
        d = json.loads(r.stdout)
    except (ValueError, TypeError):
        return {"health": "unknown", "branch": ""}
    branch = d.get("headRefName", "")
    rollup = d.get("statusCheckRollup") or []

    def state(c: dict) -> str:
        return str(c.get("conclusion") or c.get("state") or "").upper()

    if any(state(c) in _BAD_CHECK for c in rollup):
        return {"health": "failing", "branch": branch}
    if str(d.get("mergeStateStatus", "")).upper() == "BEHIND":
        return {"health": "behind", "branch": branch}
    return {"health": "healthy", "branch": branch}


def refresh_branch(repo: str, number: int, run=connect._run) -> str:
    """Merge the base (main) into the PR branch via GitHub's `update-branch`, so its CI re-runs against the
    CURRENT main. Returns one of:
      - "refreshed": the branch was behind and is now being updated (its CI will re-run).
      - "current":   the branch is already up to date with main (nothing to do).
      - "conflict":  the branch conflicts with main and can't be auto-updated (→ recreate).
      - "error":     update-branch couldn't be reached (degrade gracefully — caller falls back).
    Idempotent: re-running it when already current is a harmless "current"."""
    r = run(["gh", "api", "-X", "PUT", f"repos/{repo}/pulls/{number}/update-branch",
             "-H", "Accept: application/vnd.github+json"])
    if r.returncode == 0:
        return "refreshed"
    msg = (r.stderr or r.stdout or "").lower()
    if "conflict" in msg:
        return "conflict"
    # update-branch answers 422 when the head is already up to date with the base.
    if "up to date" in msg or "up-to-date" in msg or "not ahead" in msg or "no new commits" in msg:
        return "current"
    return "error"


def recover_maint_pr(repo: str, number: int, branch: str, health: str, run=connect._run) -> tuple[str, str]:
    """Unstick a maint PR from the CLI. Returns (mode, message):
      - "wait":     recovered in place (refreshed against main, or re-ran failed CI) — keep waiting.
      - "recreate": closed the dead PR — caller should ship a fresh one on current main.

    A maint branch that forked before a migration fails the NEW gates forever if we only re-run its CI on
    the stale branch (the #467 trap). So FIRST refresh it with current main — that heals a PR that's behind,
    OR failing *because* it's behind. Re-running `emkeel update` repeats this idempotently."""
    outcome = refresh_branch(repo, number, run)
    if outcome == "refreshed":
        return "wait", (f"  PR #{number} was behind main — refreshed it (merged current main in); its CI "
                        "re-runs against the latest state and it merges when green.")
    if outcome == "conflict":
        run(["gh", "pr", "close", str(number), "-R", repo, "--delete-branch"])
        return "recreate", (f"  PR #{number} conflicts with main — closed it; re-shipping a fresh one on "
                            "current main (it'll merge when the gates pass).")
    # "current"/"error": the branch is already up to date with main (or update-branch was unreachable).
    if health == "behind":                       # behind but couldn't refresh → just keep waiting on its CI
        return "wait", f"  PR #{number} is up to date with main — waiting for its CI to settle."
    # health == "failing" and the branch is current → a genuine failure: re-run its failed jobs.
    rl = run(["gh", "run", "list", "-R", repo, "--branch", branch, "--status", "failure",
              "--limit", "1", "--json", "databaseId", "--jq", ".[0].databaseId"])
    rid = (rl.stdout or "").strip()
    if not rid:
        return "wait", (f"  PR #{number} stuck (CI failed, branch current) — no failed run was found to "
                        "rerun; check it manually.")
    rr = run(["gh", "run", "rerun", rid, "-R", repo, "--failed"])
    if rr.returncode == 0:
        return "wait", (f"  PR #{number} stuck (CI failed, branch current) — re-ran its failed checks "
                        f"(run {rid}); it'll merge when green.")
    return "wait", (f"  PR #{number} stuck (CI failed) — couldn't rerun ({(rr.stderr or rr.stdout).strip()}); "
                    "check it manually.")


def _default_branch(run, target: Path, repo: str) -> str:
    if repo:
        r = run(["gh", "api", f"repos/{repo}", "--jq", ".default_branch"])
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    r = run(["git", "-C", str(target), "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"])
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip().rsplit("/", 1)[-1]
    return "main"


def _ship_via_worktree(mutate, summary: str, target: Path, run) -> int:
    """Run `mutate(worktree_path)` on a fresh checkout of origin/<default> and ship the result."""
    if not connect.gh_ok(run):
        print("  gh is not authenticated — run `gh auth login`, then re-run.")
        return 1
    cfg = load_cfg(target)
    if cfg is None or not cfg.github_repo:
        print("  No emkeel.toml here — run `emkeel setup` first.")
        return 1
    repo = cfg.github_repo
    # A refresh may already be shipped and waiting on auto-merge. If it's HEALTHY, don't re-push (that's
    # the non-fast-forward error) — point the user at the open PR. But if it's STUCK (its CI failed, or it's
    # behind the base), recover it from the CLI instead of dead-ending — otherwise the operator can't
    # unstick it from the console at all.
    existing = inflight_maint_pr(repo, run)
    if existing is not None:
        status = maint_pr_status(repo, existing, run)
        if status["health"] in ("healthy", "unknown"):     # unknown → offline-safe: behave as before (wait)
            print(f"  Already shipped as PR #{existing}, pending auto-merge — nothing re-pushed. "
                  f"Run `git pull` once it lands.")
            return 0
        mode, msg = recover_maint_pr(repo, existing, status["branch"], status["health"], run)
        print(msg)
        if mode == "wait":
            return 0
        # mode == "recreate": the dead PR was closed — fall through and ship a fresh one.
    default = _default_branch(run, target, repo)
    if run(["git", "-C", str(target), "fetch", "-q", "origin", default]).returncode != 0:
        print(f"  could not fetch origin/{default} — is the repo pushed to GitHub?")
        return 1
    sha = run(["git", "-C", str(target), "rev-parse", "--short", f"origin/{default}"]).stdout.strip() or "base"
    from emkeel import __version__
    branch = f"{MAINT_PREFIX}{__version__}-{sha}"

    wt = tempfile.mkdtemp(prefix="emkeel-maint-")
    try:
        r = run(["git", "-C", str(target), "worktree", "add", "-q", "-B", branch, wt, f"origin/{default}"])
        if r.returncode != 0:
            print(f"  worktree add failed: {(r.stderr or r.stdout).strip()}")
            return 1
        mutate(Path(wt))                                  # caller writes the emkeel changes here
        # A version-stamp bump of emkeel.toml is noise ONLY when it's the SOLE change — drop it then so
        # we don't open an empty PR. But when the wiring genuinely refreshed (workflows/other files
        # changed too), KEEP the bump so `generated_with` advances WITH the refresh instead of going
        # stale — reverting it there would ship refreshed wiring stamped at the old version.
        toml = Path(wt) / "emkeel.toml"
        if toml.is_file():
            head = run(["git", "-C", wt, "show", "HEAD:emkeel.toml"]).stdout
            stamp_only = _strip_stamp(toml.read_text(encoding="utf-8")) == _strip_stamp(head)
            dirty = [ln[3:].strip() for ln in
                     run(["git", "-C", wt, "status", "--porcelain"]).stdout.splitlines() if ln.strip()]
            if stamp_only and dirty == ["emkeel.toml"]:   # nothing but the stamp moved → pure noise
                run(["git", "-C", wt, "checkout", "-q", "--", "emkeel.toml"])
        if not run(["git", "-C", wt, "status", "--porcelain"]).stdout.strip():
            print(f"  origin/{default} is already current — nothing to ship.")
            return 0
        run(["git", "-C", wt, "add", "-A"])
        run(["git", "-C", wt, "commit", "-q", "-m", f"chore: {summary}"])
        print(f"  Shipping via {branch} (a pre-push hook may run — Ctrl-C to skip)…")
        if run(["git", "-C", wt, "push", "-q", "-u", "origin", branch], capture=False).returncode != 0:
            print("  push failed.")
            return 1
        pr = run(["gh", "pr", "create", "-R", repo, "--head", branch, "--base", default,
                  "--title", f"chore: {summary}", "--body", "Automated Emkeel maintenance (scope-gated lane)."])
        if pr.returncode != 0:
            print(f"  PR create: {(pr.stderr or pr.stdout).strip()}")
            return 1
        pr_url = (pr.stdout or "").strip()
        print(f"  PR opened: {pr_url}")
        connect.allow_auto_merge(repo, run)
        m = run(["gh", "pr", "merge", branch, "-R", repo, "--auto", "--squash"])
        print("  ✓ auto-merge enabled — it lands when the gates pass."
              if m.returncode == 0 else f"  auto-merge: {(m.stderr or m.stdout).strip()}")
        ref = f"PR #{pr_url.rstrip('/').rsplit('/', 1)[-1]}" if pr_url else "the PR"
        print(f"  Note: this applies asynchronously — {ref} merges once CI passes (~min). Until then "
              f"`emkeel doctor` will still show drift here; run `git pull` after it merges.")
        return 0
    finally:
        run(["git", "-C", str(target), "worktree", "remove", "--force", wt])
        shutil.rmtree(wt, ignore_errors=True)


def _strip_stamp(text: str) -> str:
    """emkeel.toml minus its `generated_with` version-stamp line (the stamp differs by version)."""
    return "\n".join(ln for ln in text.splitlines() if not ln.strip().startswith("generated_with"))


def _clean_local(target: Path, run) -> None:
    """Remove emkeel-generated changes from the working tree so they don't sit pending or pollute
    your own commits. ONLY touches files Emkeel owns (the `_files` set) and ONLY when the change is
    Emkeel's own (a regenerated file, or just emkeel.toml's version stamp) — never your product work,
    your specs/records, or real edits (e.g. a project_key you changed)."""
    from emkeel.init import _files
    cfg = load_cfg(target)
    if cfg is None:
        return
    for path, expected in _files(cfg).items():
        fp = target / path
        if not fp.is_file():
            continue
        status = run(["git", "-C", str(target), "status", "--porcelain", "--", path]).stdout
        if not status.strip():
            continue                                  # not dirty
        local = fp.read_text(encoding="utf-8")
        if path == "emkeel.toml":
            # clean only when the sole change is the version stamp; keep real value edits.
            committed = run(["git", "-C", str(target), "show", f"HEAD:{path}"]).stdout
            if _strip_stamp(local) != _strip_stamp(committed):
                continue
        elif local != expected:
            continue                                  # you hand-edited it → leave it alone
        if status.lstrip().startswith("?"):
            fp.unlink()                               # untracked emkeel file → remove
        else:
            run(["git", "-C", str(target), "checkout", "-q", "--", path])   # revert tracked


def ship_update(target: Path = Path("."), run=connect._run) -> int:
    """Refresh the wiring on origin/<default> (regenerate from its own committed config), ship it,
    then clean any local emkeel leftovers from your working tree."""
    from emkeel.init import apply

    def mutate(wt: Path):
        apply(wt, load_cfg(wt), force=True, dry_run=False)
    from emkeel import __version__
    rc = _ship_via_worktree(mutate, f"refresh emkeel wiring ({__version__})", target, run)
    if rc == 0:
        _clean_local(target, run)
    return rc


def ship_set(attr: str, value: str, target: Path = Path("."), run=connect._run) -> int:
    """Change one emkeel.toml field on origin/<default>, ship it, then clean local leftovers."""
    from emkeel.init import _toml

    def mutate(wt: Path):
        cfg = load_cfg(wt)
        setattr(cfg, attr, value)
        (wt / "emkeel.toml").write_text(_toml(cfg), encoding="utf-8")
    rc = _ship_via_worktree(mutate, f"set {attr} = {value} (emkeel.toml)", target, run)
    if rc == 0:
        _clean_local(target, run)
    return rc
