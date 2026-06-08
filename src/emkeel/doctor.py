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


def _gates_required(repo: str, branch: str, run=_run) -> bool:
    """True if the 'gates' check is required on `branch` — via classic protection OR a ruleset."""
    classic = run(["gh", "api", f"repos/{repo}/branches/{branch}/protection",
                   "--jq", ".required_status_checks.contexts"])
    if classic.returncode == 0 and "gates" in classic.stdout:
        return True
    rules = run(["gh", "api", f"repos/{repo}/rules/branches/{branch}",
                 "--jq", '[.[] | select(.type=="required_status_checks") | .parameters.required_status_checks[].context]'])
    return rules.returncode == 0 and "gates" in rules.stdout


def gather(target: Path) -> dict:
    """Inspect repo + GitHub state. gh-dependent checks stay None when they can't be determined."""
    st = {"governed": (target / "emkeel.toml").is_file(), "repo": "", "connected": False,
          "gh_ok": False, "secrets_ok": None, "protection_ok": None, "default_branch": "main",
          "drift": []}
    if st["governed"]:
        from emkeel.update import wiring_drift
        st["drift"] = wiring_drift(target)   # generated files that `emkeel update` would refresh
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
    st["protection_ok"] = _gates_required(st["repo"], st["default_branch"])
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
    out.append(f"  {ok(st.get('protection_ok'))} 'gates' check required (enforcement on)"
               + ("" if st.get("protection_ok") else f"   → https://github.com/{repo}/settings/branches"))
    pending = [k for k in ("secrets_ok", "protection_ok") if not st.get(k)]
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
