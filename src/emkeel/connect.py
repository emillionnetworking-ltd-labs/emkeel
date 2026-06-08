"""emkeel connect — automate the GitHub side via `gh`.

Leaves only one manual step: creating the Jira API token (on Atlassian). You paste it into a
hidden prompt here — it never goes through an AI chat. Everything is confirmed before it runs.

- **New project** (not on GitHub yet): create + push the repo, then branch protection + secrets.
- **Existing repo**: branch protection + secrets. (Pushing the adopt branch stays manual — a
  pre-push hook could hang; that belongs to the AI-interpreter, not a deterministic command.)

`--dry-run` prints the gh commands without running anything. If gh isn't available/authed, it
points you to the web links (same as `emkeel doctor`).
"""

from __future__ import annotations

import argparse
import getpass as _getpass
import json
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path

TOKEN_LINK = "https://id.atlassian.net/manage-profile/security/api-tokens"


def _run(args: list[str], stdin: str | None = None, timeout: float | None = None,
         capture: bool = True) -> subprocess.CompletedProcess:
    if capture:
        return subprocess.run(args, capture_output=True, text=True, input=stdin, timeout=timeout)
    return subprocess.run(args, text=True, timeout=timeout)   # inherit the terminal (prompts/hooks visible)


def _yes(s: str) -> bool:
    return s.strip().lower() in ("", "y", "yes", "s", "si")


@dataclass
class Cfg:
    repo: str
    base_url: str


def load_config(target: Path) -> Cfg | None:
    p = target / "emkeel.toml"
    if not p.is_file():
        return None
    data = tomllib.loads(p.read_text(encoding="utf-8"))
    return Cfg(repo=data.get("github", {}).get("repo", ""),
               base_url=data.get("jira", {}).get("base_url", ""))


def protection_body(checks=("gates",)) -> dict:
    """Classic branch-protection body: require the checks + a PR; solo-friendly (0 approvals)."""
    return {
        "required_status_checks": {"strict": False, "contexts": list(checks)},
        "enforce_admins": False,
        "required_pull_request_reviews": {"required_approving_review_count": 0},
        "restrictions": None,
    }


def gh_ok(run=_run) -> bool:
    return run(["gh", "auth", "status"]).returncode == 0


def repo_exists(repo: str, run=_run) -> bool:
    return run(["gh", "repo", "view", repo]).returncode == 0


def do_create_push(repo: str, run=_run):
    r = run(["gh", "repo", "create", repo, "--private", "--source=.", "--push"])
    return r.returncode == 0, (r.stderr or r.stdout).strip()


def do_protect(repo: str, branch: str, run=_run):
    r = run(["gh", "api", "-X", "PUT", f"repos/{repo}/branches/{branch}/protection", "--input", "-"],
            stdin=json.dumps(protection_body()))
    return r.returncode == 0, (r.stderr or r.stdout).strip()


def do_secret(repo: str, name: str, value: str, run=_run):
    r = run(["gh", "secret", "set", name, "--repo", repo, "--body", value])
    return r.returncode == 0, (r.stderr or r.stdout).strip()


def current_branch(run=_run) -> str:
    r = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    return r.stdout.strip() if r.returncode == 0 else ""


def do_push(run=_run):
    """Push HEAD inheriting the terminal, so a pre-push hook / SSH passphrase / credential prompt
    is visible and answerable (capturing it would hang silently). Ctrl-C cancels cleanly."""
    try:
        r = run(["git", "push", "-u", "origin", "HEAD"], capture=False)
    except subprocess.TimeoutExpired:
        return False, "timed out (a pre-push hook may be hanging)"
    except KeyboardInterrupt:
        return False, "cancelled (Ctrl-C)"
    return r.returncode == 0, (getattr(r, "stderr", "") or "").strip()


def do_pr_create(run=_run):
    r = run(["gh", "pr", "create", "--fill"])
    return r.returncode == 0, (r.stdout or r.stderr).strip()


def do_auto_merge(run=_run):
    """Enable GitHub's native auto-merge: merges WHEN required checks pass (gates) + approvals met."""
    r = run(["gh", "pr", "merge", "--auto", "--squash"])
    return r.returncode == 0, (r.stderr or r.stdout).strip()


def main(argv=None, inp=input, getpass=_getpass.getpass, run=_run) -> int:
    ap = argparse.ArgumentParser(prog="emkeel connect", description="Automate the GitHub side via gh.")
    ap.add_argument("--branch", default="main")
    ap.add_argument("--dry-run", action="store_true")
    ns = ap.parse_args(argv if argv is not None else None)

    cfg = load_config(Path("."))
    if cfg is None or not cfg.repo:
        print("  No emkeel.toml here — run `emkeel setup` first.")
        return 1
    repo, branch = cfg.repo, ns.branch
    print(f"\n  emkeel connect → {repo}\n  " + "─" * 22)

    if ns.dry_run:
        print("  Would run (gh):")
        print(f"    • gh repo create {repo} --private --source=. --push   (only if not on GitHub yet)")
        print(f"    • gh api -X PUT repos/{repo}/branches/{branch}/protection   (require 'gates' + PR)")
        print(f"    • gh secret set JIRA_BASE_URL / JIRA_EMAIL / JIRA_TOKEN --repo {repo}")
        print(f"    • (adopt branch) git push -u origin HEAD ; gh pr create --fill ; gh pr merge --auto --squash")
        print(f"  Manual (only you): create the Jira token → {TOKEN_LINK}")
        return 0

    if not gh_ok(run):
        print("  gh isn't authenticated. Run `gh auth login` and retry — or use the web links from `emkeel doctor`.")
        return 1

    # 1) New project? establish the GitHub connection first (safe: a fresh repo has no hooks).
    if not repo_exists(repo, run):
        if _yes(inp("  Repo isn't on GitHub yet. Create it (private) and push? [Y/n] ")):
            ok, msg = do_create_push(repo, run)
            print("  ✓ repo created + pushed" if ok else f"  ✗ {msg}")
            if not ok:
                print(f"     Create it manually:  gh repo create {repo} --private --source=. --push")
                print("     Then re-run:  emkeel connect")
                return 1

    # 2) Branch protection — require the gates check + PRs
    if _yes(inp(f"  Require the 'gates' check + PRs on '{branch}'? [Y/n] ")):
        ok, msg = do_protect(repo, branch, run)
        print("  ✓ branch protection on" if ok else f"  ✗ {msg}\n     (need admin rights? do it via the web link)")

    # 3) Secrets — token via hidden prompt; never in chat or logs
    if _yes(inp("  Set the Jira secrets now? (you'll paste the token, hidden) [Y/n] ")):
        print(f"  Create the token first if you haven't: {TOKEN_LINK}")
        email = inp("  Atlassian email: ").strip()
        token = getpass("  Jira API token (hidden): ").strip()
        for name, val in (("JIRA_BASE_URL", cfg.base_url), ("JIRA_EMAIL", email), ("JIRA_TOKEN", token)):
            ok, msg = do_secret(repo, name, val, run)
            print(f"  {'✓' if ok else '✗'} {name}" + ("" if ok else f": {msg}"))

    # 4) Finish the adopt — push the branch, open a PR, auto-merge when gates pass.
    #    Scope: the emkeel ADOPTION PR only (you're on its branch). Normal changes stay human-merged.
    cur = current_branch(run)
    if cur and cur != branch:
        ans = inp(f"  Finish the adopt — push '{cur}', open a PR and auto-merge when gates pass? [y/N] ").strip().lower()
        if ans in ("y", "yes", "s", "si"):
            print("  Pushing… (you'll see git's output; a pre-push hook may take a moment — Ctrl-C to skip)")
            ok, msg = do_push(run)
            if not ok:
                print(f"  ✗ push: {msg}")
                print("     Do it manually:  git push -u origin HEAD  &&  gh pr create --fill  &&  gh pr merge --auto --squash")
            else:
                print("  ✓ pushed")
                okp, out = do_pr_create(run)
                print(f"  ✓ PR opened — {out}" if okp else f"  ✗ gh pr create: {out}")
                if okp:
                    okm, outm = do_auto_merge(run)
                    print("  ✓ auto-merge on — merges when the gates pass" if okm
                          else f"  ⚠ auto-merge: {outm}\n     (gates failed? fix + push again; or merge it yourself once green)")

    print("\n  Done. Check with: emkeel doctor")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
