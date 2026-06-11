"""emkeel update — refresh the generated wiring to the installed version.

New adoptions get the latest templates automatically; an already-adopted repo is frozen at its
adoption version (`pipx upgrade` updates the tool, not your repo's files). `emkeel update` reads
your `emkeel.toml` and re-applies the wiring (AGENTS.md, CLAUDE.md, workflows, .env.example) with
the current templates — your values and `emkeel-governance/` are preserved. No manual editing.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from emkeel.init import Config


def load_cfg(target: Path) -> Config | None:
    p = target / "emkeel.toml"
    if not p.is_file():
        return None
    d = tomllib.loads(p.read_text(encoding="utf-8"))
    cfg = Config(
        jira_url=d.get("jira", {}).get("base_url", ""),
        jira_project=d.get("jira", {}).get("project_key", ""),
        github_repo=d.get("github", {}).get("repo", ""),
    )
    src = d.get("emkeel", {}).get("source")
    if src:                       # preserve a custom (e.g. private-fork) install pin — don't clobber it
        cfg.emkeel_source = src
    return cfg


def _origin_default(target: Path) -> str | None:
    """The repo's default branch on origin (main/master/…), or None if there's no usable origin."""
    import subprocess
    if "origin" not in subprocess.run(["git", "-C", str(target), "remote"],
                                      capture_output=True, text=True).stdout.split():
        return None
    r = subprocess.run(["git", "-C", str(target), "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"],
                       capture_output=True, text=True)
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip().rsplit("/", 1)[-1]
    if subprocess.run(["git", "-C", str(target), "rev-parse", "--verify", "-q", "origin/main"],
                      capture_output=True).returncode == 0:
        return "main"
    return None


def origin_jira_project(target: Path) -> str:
    """The project_key declared on origin/<default> (the governance source of truth), so a feature
    branch that still declares the old key doesn't show a false concordance warning. Local fallback
    when there's no remote."""
    import subprocess
    import tomllib
    default = _origin_default(target)
    if default:
        r = subprocess.run(["git", "-C", str(target), "show", f"origin/{default}:emkeel.toml"],
                           capture_output=True, text=True)
        if r.returncode == 0:
            try:
                return tomllib.loads(r.stdout).get("jira", {}).get("project_key", "")
            except Exception:
                return ""
    cfg = load_cfg(target)
    return cfg.jira_project if cfg else ""


def wiring_drift(target: Path) -> list[str]:
    """Generated files whose canonical copy differs from what the current Emkeel would write
    (`emkeel update` would change them). Measured against origin/<default> — the governance source
    of truth — when there's a remote, so a feature branch behind main does NOT show as drift; against
    the local tree otherwise. Excludes emkeel.toml (its version stamp always differs)."""
    cfg = load_cfg(target)
    if cfg is None:
        return []
    import subprocess

    from emkeel.init import _files
    default = _origin_default(target)
    drift = []
    for path, content in _files(cfg).items():
        if path == "emkeel.toml":
            continue
        if default:
            r = subprocess.run(["git", "-C", str(target), "show", f"origin/{default}:{path}"],
                               capture_output=True, text=True)
            committed = r.stdout if r.returncode == 0 else ""   # missing on origin → counts as drift
            if committed != content:
                drift.append(path)
        elif (target / path).is_file() and (target / path).read_text(encoding="utf-8") != content:
            drift.append(path)
    return drift


def main(argv: list[str] | None = None) -> int:
    no_ship = "--no-ship" in (argv or [])
    target = Path(".")
    cfg = load_cfg(target)
    if cfg is None or not cfg.github_repo:
        print("  No emkeel.toml here — run `emkeel setup` first.")
        return 1

    if not no_ship:
        # Default: refresh + ship in an isolated worktree — never touches YOUR working tree.
        from emkeel.ship import ship_update
        return ship_update(target)

    # --no-ship: refresh the LOCAL working tree (you commit it yourself).
    from emkeel.init import APPEND_LINES, _files
    results: list[tuple[str, str]] = []   # (status, path) — status: created|updated|appended|unchanged
    for path, content in _files(cfg).items():
        p = target / path
        existed = p.is_file()
        if existed and p.read_text(encoding="utf-8") == content:
            results.append(("unchanged", path))
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        results.append(("updated" if existed else "created", path))
    for path, line in APPEND_LINES.items():
        p = target / path
        if p.is_file() and line in p.read_text(encoding="utf-8").splitlines():
            results.append(("unchanged", path))
            continue
        prev = p.read_text(encoding="utf-8") if p.is_file() else ""
        sep = "" if (prev == "" or prev.endswith("\n")) else "\n"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(prev + sep + line + "\n", encoding="utf-8")
        results.append(("appended", path))

    changed = [(s, p) for s, p in results if s != "unchanged"]
    if not changed:
        print("emkeel update — already current; nothing to change.")
        return 0
    print("emkeel update — refreshed the wiring (local; --no-ship):")
    for s, p in changed:
        print(f"  {s:10} {p}")
    n_un = len(results) - len(changed)
    if n_un:
        print(f"  ({n_un} file(s) already current)")
    print("\n(--no-ship: commit the refreshed files yourself, or run `emkeel update` to ship them)")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
