"""Auto-ship emkeel-managed changes through a scope-gated maintenance lane.

Used by `emkeel update` / `emkeel set` (ship-by-default; `--no-ship` opts out) so a wiring refresh
never sits uncommitted — but still goes through a PR + the gates (NEVER a direct push to main).

The lane: a branch `emkeel-maint/<version>-<sha>` forked from the DEFAULT branch (so it doesn't
matter which branch you're on), committing ONLY the emkeel-managed files. The `check_ticket_link`
gate accepts this branch without a Jira ticket because `check_maint_scope` verifies the PR touches
nothing but emkeel-managed files — a bounded, self-policing exemption, not a blanket bypass.
"""

from __future__ import annotations

from pathlib import Path

from emkeel import connect

MAINT_PREFIX = "emkeel-maint/"


def _default_branch(run, target: Path, repo: str) -> str:
    if repo:
        r = run(["gh", "api", f"repos/{repo}", "--jq", ".default_branch"])
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    r = run(["git", "-C", str(target), "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"])
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip().rsplit("/", 1)[-1]
    return "main"


def ship(paths: list[str], target: Path = Path("."), run=connect._run) -> int:
    paths = [p for p in paths if (target / p).exists()]
    if not paths:
        print("  Nothing to ship.")
        return 0
    if not connect.gh_ok(run):
        print("  gh is not authenticated — run `gh auth login`, then commit/push yourself.")
        return 1

    # Refuse if there are OTHER uncommitted changes — the lane must carry only emkeel files.
    status = run(["git", "-C", str(target), "status", "--porcelain"])
    dirty = [ln[3:] for ln in status.stdout.splitlines() if ln.strip()]
    stray = [f for f in dirty if f not in paths]
    if stray:
        print(f"  You have other uncommitted changes ({', '.join(stray[:3])}…) — "
              "commit or stash them first, then re-run.")
        return 1

    cfg = connect.load_config(target)
    repo = cfg.repo if cfg else ""
    default = _default_branch(run, target, repo)
    orig = run(["git", "-C", str(target), "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
    content = {p: (target / p).read_text(encoding="utf-8") for p in paths}

    run(["git", "-C", str(target), "fetch", "-q", "origin", default])
    sha = run(["git", "-C", str(target), "rev-parse", "--short", f"origin/{default}"]).stdout.strip() or "base"
    from emkeel import __version__
    branch = f"{MAINT_PREFIX}{__version__}-{sha}"

    run(["git", "-C", str(target), "checkout", "--", *paths])   # clean our paths so the switch is clean
    if run(["git", "-C", str(target), "checkout", "-B", branch, f"origin/{default}"]).returncode != 0:
        print(f"  could not fork the maintenance branch from origin/{default}.")
        return 1
    for p, c in content.items():
        (target / p).write_text(c, encoding="utf-8")
    run(["git", "-C", str(target), "add", *paths])
    commit = run(["git", "-C", str(target), "commit", "-m", f"chore: refresh emkeel wiring ({__version__})"])
    blob = ((commit.stdout or "") + (commit.stderr or "")).lower()
    if commit.returncode != 0 and "nothing to commit" not in blob:
        print(f"  commit failed: {(commit.stderr or commit.stdout).strip()}")
        if orig:
            run(["git", "-C", str(target), "checkout", "-q", orig])
        return 1

    print(f"  Shipping via {branch} (a pre-push hook may run — Ctrl-C to skip)…")
    ok, msg = connect.do_push(run)
    if not ok:
        print(f"  push failed: {msg}")
        return 1
    ok, msg = connect.do_pr_create(run)
    if not ok:
        print(f"  PR create: {msg}")
        return 1
    print(f"  PR opened: {msg}")
    if repo:
        connect.allow_auto_merge(repo, run)
    ok, msg = connect.do_auto_merge(run)
    print("  ✓ auto-merge enabled — it lands when the gates pass." if ok else f"  auto-merge: {msg}")
    if orig:
        run(["git", "-C", str(target), "checkout", "-q", orig])   # return you to where you were
    return 0
