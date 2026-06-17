"""emkeel doctor — health check: what's set up, and what's still pending (with fix links).

Run `emkeel doctor` anytime. It checks: the repo is governed (emkeel.toml), it's connected to
GitHub, `gh` is authenticated, the Jira secrets are set, and the `gates` check is required.
New-project aware: with no GitHub remote yet, it tells you to create + push the repo first.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True)


def _required_contexts(repo: str, branch: str, run=None) -> set[str] | None:
    """The set of status-check contexts enforced on `branch` — classic protection ∪ ruleset.

    Returns None when it can't be determined at all (both API calls error), so the caller can show '?'
    instead of a false 'nothing enforced'. Each `gh --jq` streams one context per line."""
    run = run or _run                       # resolve at call time so a monkeypatched _run is honored
    contexts: set[str] = set()
    determined = False
    classic = run(["gh", "api", f"repos/{repo}/branches/{branch}/protection",
                   "--jq", ".required_status_checks.contexts[]?"])
    if classic.returncode == 0:
        determined = True
        contexts |= {c.strip() for c in classic.stdout.splitlines() if c.strip()}
    rules = run(["gh", "api", f"repos/{repo}/rules/branches/{branch}",
                 "--jq", '.[]? | select(.type=="required_status_checks") | .parameters.required_status_checks[].context'])
    if rules.returncode == 0:
        determined = True
        contexts |= {c.strip() for c in rules.stdout.splitlines() if c.strip()}
    return contexts if determined else None


def gather(target: Path) -> dict:
    """Inspect repo + GitHub state. gh-dependent checks stay None when they can't be determined."""
    st = {"governed": (target / "emkeel.toml").is_file(), "repo": "", "connected": False,
          "gh_ok": False, "secrets_ok": None, "protection_ok": None, "default_branch": "main",
          "drift": [], "jira_project": "", "branch_key": "", "required_checks": ["gates"],
          "required_missing": []}
    if st["governed"]:
        from emkeel.update import load_cfg, origin_jira_project, wiring_drift
        st["drift"] = wiring_drift(target)   # generated files that `emkeel update` would refresh
        st["jira_project"] = origin_jira_project(target)   # project on origin/<default>, not the local branch
        cfg = load_cfg(target)
        if cfg:
            st["required_checks"] = cfg.required_checks
        br = _run(["git", "-C", str(target), "branch", "--show-current"])
        bm = re.search(r"[A-Z][A-Z0-9]+-\d+", br.stdout) if br.returncode == 0 else None
        st["branch_key"] = bm.group(0) if bm else ""
    r = _run(["git", "-C", str(target), "remote", "get-url", "origin"])
    if r.returncode == 0:
        m = re.search(r"github\.com[:/]+([^/]+/[^/.\s]+)", r.stdout.strip())
        if m:
            st["repo"], st["connected"] = m.group(1), True
    if not st["connected"]:
        return st
    st["gh_ok"] = _run(["gh", "auth", "status"]).returncode == 0
    if not st["gh_ok"]:
        return st
    db = _run(["gh", "api", f"repos/{st['repo']}", "--jq", ".default_branch"])
    if db.returncode == 0 and db.stdout.strip():
        st["default_branch"] = db.stdout.strip()
    sl = _run(["gh", "secret", "list", "--repo", st["repo"]])
    if sl.returncode == 0:
        st["secrets_ok"] = all(k in sl.stdout for k in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_TOKEN"))
    enforced = _required_contexts(st["repo"], st["default_branch"])
    if enforced is None:                 # branch protection couldn't be read — leave as '?', don't fail
        st["protection_ok"] = None
        st["required_missing"] = []
    else:
        # `gates` is always required (emkeel's own, non-negotiable); union it with the declared set.
        declared = {"gates"} | set(st["required_checks"])
        st["protection_ok"] = "gates" in enforced
        st["required_missing"] = sorted(declared - enforced)
    return st


def report_lines(st: dict) -> list[str]:
    """Human-readable PASS/MISSING report (with fix links). Pure — easy to test."""
    def ok(b):  # ✓ / ✗
        return "✓" if b else "✗"
    repo = st.get("repo") or "OWNER/REPO"
    out = ["", "  emkeel doctor", "  " + "─" * 14]
    out.append(f"  {ok(st.get('governed'))} repo governed (emkeel.toml)"
               + ("" if st.get("governed") else "   → run: emkeel setup"))
    if st.get("governed") and st.get("drift"):
        out.append(f"  ⚠ {len(st['drift'])} wiring file(s) out of date ({', '.join(st['drift'])})"
                   "   → run: emkeel update")
    jp, bk = st.get("jira_project"), st.get("branch_key")
    if jp and bk and bk.split("-")[0] != jp:
        out.append(f"  ⚠ branch '{bk}' ≠ configured Jira project '{jp}'"
                   "   → align emkeel.toml or the branch key")
    if not st.get("connected"):
        out += ["  ✗ not connected to GitHub yet",
                "      → create + push the repo:  gh repo create --source=. --push",
                "      (then re-run: emkeel doctor)"]
        return out
    out.append(f"  ✓ connected to GitHub ({repo})")
    if not st.get("gh_ok"):
        out += ["  ? secrets / branch protection — can't check from here",
                "      → install gh and run: gh auth login"]
        return out
    out.append(f"  {ok(st.get('secrets_ok'))} Jira secrets set (JIRA_BASE_URL / JIRA_EMAIL / JIRA_TOKEN)"
               + ("" if st.get("secrets_ok") else f"   → https://github.com/{repo}/settings/secrets/actions/new"))
    branch = st.get("default_branch", "main")
    po = st.get("protection_ok")
    if po is None:
        out.append("  ? 'gates' check required — couldn't read branch protection"
                   f"   → check: https://github.com/{repo}/settings/branches")
    else:
        out.append(f"  {ok(po)} 'gates' check required (enforcement on)"
                   + ("" if po else f"   → https://github.com/{repo}/settings/branches"))
    # Declared required checks beyond `gates` that aren't enforced → drift, with the exact fix command.
    extra_missing = [c for c in st.get("required_missing", []) if c != "gates"]
    for c in extra_missing:
        out.append(f"  ✗ required check '{c}' declared but NOT enforced"
                   f"   → gh api -X POST repos/{repo}/branches/{branch}/protection/required_status_checks/contexts"
                   f" -f 'contexts[]={c}'")
    extra_declared = [c for c in st.get("required_checks", []) if c != "gates"]
    if extra_declared and not extra_missing and po is not None:
        out.append(f"  ✓ required checks enforced: {', '.join(extra_declared)}")
    pending = [k for k in ("secrets_ok", "protection_ok") if not st.get(k)] + extra_missing
    out.append("")
    out.append("  All set ✓" if not pending else f"  {len(pending)} step(s) pending — see ✗ above.")
    return out


def main(argv: list[str] | None = None) -> int:
    for line in report_lines(gather(Path("."))):
        print(line)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
