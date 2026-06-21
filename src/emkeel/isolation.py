"""Per-repo agent isolation — fail-safe deny of UNAMBIGUOUS cross-repo actions.

An agent working in repo X's window must not reach into repo Y's filesystem / GitHub / Jira. VS Code
windows are cosmetic; `gh`, the Jira API and absolute paths are not restricted by them. This module is
the enforcement: a Claude Code **PreToolUse hook** calls `emkeel guard`, which reads this repo's identity
from `emkeel.toml` (`[github] repo`, `[jira] project_key`) and DENIES only clear crossings.

FAIL-SAFE IS THE PRIME DIRECTIVE: a hook that over-denies BRICKS the agent. So `decide` denies ONLY
unambiguous cross-repo actions and ALLOWS everything else — anything in-repo, ambiguous, or undecidable
(no identity, parse error, scratch dirs like /tmp) is allowed. "Another repo" means a sibling project
under the same parent directory (the `projects/<repo>` layout the incident came from), never `/tmp`/`~`.

Pure + stdlib only: `decide` is a pure function of its inputs (testable without a filesystem or network);
only `find_identity` and `main` touch disk/stdin.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tomllib
from pathlib import Path
from urllib.parse import urlparse

ALLOW: tuple[str, str] = ("allow", "")

# Mutating file tools whose target we protect (Read is not mutating → never auto-protected).
_MUTATING = {"Edit", "Write", "NotebookEdit", "MultiEdit"}

# Guard/identity config an agent must not silently rewrite (would disable its own isolation).
_PROTECTED_RE = re.compile(r"(?:^|/)(?:\.claude/settings[^/]*|\.claude/hooks/.+|emkeel\.toml)$")


# ---------- identity ----------

def find_identity(cwd: str | os.PathLike) -> dict | None:
    """Walk up from `cwd` to the nearest `emkeel.toml`; return {repo, project_key, root} or None.

    None (repo not governed / no toml) → the caller fails SAFE: it allows everything (can't define a
    boundary, so it doesn't enforce one)."""
    here = Path(cwd).resolve()
    for d in (here, *here.parents):
        toml = d / "emkeel.toml"
        if toml.is_file():
            try:
                data = tomllib.loads(toml.read_text(encoding="utf-8"))
            except (tomllib.TOMLDecodeError, OSError):
                return None
            jira = data.get("jira", {}) or {}
            base = jira.get("base_url", "") or ""
            return {
                "repo": (data.get("github", {}) or {}).get("repo", "") or "",
                "project_key": jira.get("project_key", "") or "",
                "jira_host": (urlparse(base).netloc if base else ""),   # for raw-API detection (KEEL-92)
                "root": str(d),
            }
    return None


# ---------- pure helpers ----------

def _norm_repo(value: str) -> str | None:
    """`owner/name` from a repo arg or a github URL; None if it isn't repo-shaped (→ not a crossing)."""
    v = value.strip().strip("\"'")
    m = re.search(r"github\.com[:/]+([\w.\-]+/[\w.\-]+?)(?:\.git)?/?$", v)
    if m:
        return m.group(1)
    if re.fullmatch(r"[\w.\-]+/[\w.\-]+", v):
        return v
    return None


def _crosses_repo(value: str, identity_repo: str) -> bool:
    n = _norm_repo(value)
    return n is not None and bool(identity_repo) and n != identity_repo


def _resolve(path_str: str, cwd: str) -> Path:
    p = Path(path_str.strip().strip("\"'")).expanduser()
    full = p if p.is_absolute() else Path(cwd) / p
    return Path(os.path.normpath(str(full)))


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _is_sibling_repo(target: Path, root: Path) -> bool:
    """True if `target` is OUTSIDE root but inside root's parent — i.e., a sibling project directory
    (`projects/<other-repo>`). This is the precise 'another repo' the isolation protects; scratch paths
    like /tmp or ~ are NOT under the parent, so they're never flagged (fail-safe)."""
    parent = Path(os.path.normpath(str(root))).parent
    return _is_under(target, parent) and not _is_under(target, Path(os.path.normpath(str(root))))


def _is_protected_path(path_str: str) -> bool:
    norm = path_str.replace("\\", "/").strip().strip("\"'")
    return bool(_PROTECTED_RE.search(norm)) or norm in (".claude/settings.json", "emkeel.toml")


# ---------- raw-API detection (KEEL-92): a curl/python straight to Jira/GitHub bypasses gh/emkeel ----------

def _is_jira_api(cmd: str, jira_host: str) -> bool:
    """True if the command looks like a call to the Jira REST API (this repo's host, any atlassian.net,
    or a `/rest/api/<ver>/` path)."""
    if jira_host and jira_host in cmd:
        return True
    return "atlassian.net" in cmd or bool(re.search(r"/rest/api/\w+/", cmd))


def _jira_project_keys(cmd: str) -> set[str]:
    """Project keys referenced in a Jira-API command, across the create/JQL/transition forms:
    `"project":{"key":"ECO"}`, `project=ECO`, a bare `"key":"ECO"`, and an issue key in `/issue/ECO-7`
    (→ project ECO). Issue keys (`ECO-7`) are reduced to their project prefix; never a false match on one."""
    q = r"[\"']"   # JSON (") and python-dict (') quoting both occur in raw API commands
    keys: set[str] = set()
    keys.update(re.findall(rf'{q}project{q}\s*:\s*\{{\s*{q}key{q}\s*:\s*{q}([A-Z][A-Z0-9]+){q}', cmd))
    keys.update(re.findall(r'\bproject\s*[=:]\s*"?\'?([A-Z][A-Z0-9]+)(?!-?\d)', cmd))
    keys.update(re.findall(rf'{q}key{q}\s*:\s*{q}([A-Z][A-Z0-9]+){q}', cmd))    # bare project key (ECO-7 won't match: -7 before quote)
    keys.update(re.findall(r'/issue/([A-Z][A-Z0-9]+)-\d+', cmd))               # transition/get a foreign issue
    return keys


# ---------- the decision (pure) ----------

def _decide_bash(cmd: str, cwd: str, ident: dict) -> tuple[str, str]:
    repo = ident.get("repo", "")
    proj = ident.get("project_key", "")
    root = Path(ident["root"])

    # gh ... -R/--repo <other>
    for m in re.finditer(r"(?:^|\s)(?:-R|--repo)[=\s]+(\S+)", cmd):
        if _crosses_repo(m.group(1), repo):
            return ("deny", f"emkeel isolation: this is the '{repo}' window — refusing a gh command "
                            f"targeting a different repo ({_norm_repo(m.group(1))}).")

    # emkeel jira / gh ... --project <other>
    for m in re.finditer(r"--project[=\s]+(\S+)", cmd):
        val = m.group(1).strip("\"'")
        if proj and _norm_repo(val) is None and val != proj:
            return ("deny", f"emkeel isolation: this is the '{proj}' Jira project — refusing "
                            f"--project {val}.")

    # git push to a FOREIGN github URL (a named remote like origin is the repo's own → allowed)
    if re.search(r"\bgit\s+push\b", cmd):
        for u in re.findall(r"(github\.com[:/]+[\w.\-]+/[\w.\-]+)", cmd):
            if _crosses_repo(u, repo):
                return ("deny", f"emkeel isolation: refusing git push to a different repo "
                                f"({_norm_repo(u)}); this window is '{repo}'.")

    # RAW Jira API (curl/python straight to the REST API) targeting a DIFFERENT project
    if proj and _is_jira_api(cmd, ident.get("jira_host", "")):
        foreign = sorted(k for k in _jira_project_keys(cmd) if k != proj)
        if foreign:
            return ("deny", f"emkeel isolation: this is the '{proj}' Jira project — refusing a raw Jira "
                            f"API call targeting project {', '.join(foreign)}.")

    # RAW GitHub API (api.github.com/repos/<owner>/<repo>) targeting a DIFFERENT repo
    for m in re.finditer(r"api\.github\.com/repos/([\w.\-]+/[\w.\-]+)", cmd):
        if _crosses_repo(m.group(1), repo):
            return ("deny", f"emkeel isolation: this is the '{repo}' window — refusing a raw GitHub API "
                            f"call targeting a different repo ({_norm_repo(m.group(1))}).")

    # cd into a SIBLING repo (cd ../other-repo, cd /abs/projects/other)
    for seg in re.split(r"&&|\|\||[;|]", cmd):
        seg = seg.strip()
        m = re.match(r"cd\s+(\S+)", seg)
        if m and _is_sibling_repo(_resolve(m.group(1), cwd), root):
            return ("deny", f"emkeel isolation: refusing `cd` into a sibling repo "
                            f"({m.group(1)}); this window is '{repo}'.")

    return ALLOW


def _decide_path(tool_name: str, tool_input: dict, cwd: str, ident: dict) -> tuple[str, str]:
    path = tool_input.get("file_path") or tool_input.get("path") or ""
    if not path:
        return ALLOW
    root = Path(ident["root"])
    mutating = tool_name in _MUTATING

    # auto-protection: never let an agent edit away its own guard / identity (even in-repo)
    if mutating and _is_protected_path(str(path)):
        return ("deny", f"emkeel isolation: editing {path} (the guard/identity config) is blocked — "
                        "change isolation in emkeel, not by disabling the hook locally.")

    # cross-repo: a path that resolves into a sibling project directory
    if _is_sibling_repo(_resolve(str(path), cwd), root):
        return ("deny", f"emkeel isolation: this is the '{ident.get('repo')}' window — refusing "
                        f"{tool_name} on '{path}' (it belongs to a different repo).")

    return ALLOW


def decide(tool_name: str, tool_input: dict, cwd: str, identity: dict | None) -> tuple[str, str]:
    """Return ("allow"|"deny", reason). DENIES only unambiguous cross-repo actions; allows everything
    else. `identity` None (repo not governed) → allow (no boundary to enforce)."""
    if not identity or not identity.get("root"):
        return ALLOW
    tool_input = tool_input or {}
    if tool_name == "Bash":
        return _decide_bash(str(tool_input.get("command", "")), cwd, identity)
    if tool_name in _MUTATING or tool_name == "Read":
        return _decide_path(tool_name, tool_input, cwd, identity)
    return ALLOW


# ---------- entrypoint (the hook invokes this) ----------

def main(argv: list[str] | None = None) -> int:
    """Read the Claude Code PreToolUse hook JSON on stdin, decide, and emit the harness JSON on a deny.
    ALWAYS exits 0 and, on any internal error, ALLOWS — the guard must never brick the agent."""
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0  # unreadable input → fail safe (allow)
    try:
        cwd = data.get("cwd") or os.getcwd()
        decision, reason = decide(data.get("tool_name", ""), data.get("tool_input", {}) or {},
                                  cwd, find_identity(cwd))
    except Exception:
        decision, reason = ALLOW  # any internal error → allow, never block
    if decision == "deny":
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }}))
    # allow → emit nothing: let Claude Code's normal permission flow proceed (we only ever DENY).
    return 0


if __name__ == "__main__":
    sys.exit(main())
