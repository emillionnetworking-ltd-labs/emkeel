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
    github = d.get("github", {})
    cfg = Config(
        jira_url=d.get("jira", {}).get("base_url", ""),
        jira_project=d.get("jira", {}).get("project_key", ""),
        github_repo=github.get("repo", ""),
    )
    rc = github.get("required_checks")
    if rc:                            # absent → keep the default ["gates"] (backward-compatible)
        cfg.required_checks = [str(c) for c in rc]
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

    from emkeel.init import APPEND_LINES, MERGE_FILES, _files, is_self_repo, self_exempt
    default = _origin_default(target)
    self_repo = is_self_repo(target)   # emkeel's OWN repo doesn't use the distributed CI/docs templates

    def _origin_or_local(path: str) -> str | None:
        if default:
            r = subprocess.run(["git", "-C", str(target), "show", f"origin/{default}:{path}"],
                               capture_output=True, text=True)
            return r.stdout if r.returncode == 0 else None
        p = target / path
        return p.read_text(encoding="utf-8") if p.is_file() else None

    drift = []
    for path, content in _files(cfg).items():
        if path == "emkeel.toml":
            continue
        if self_repo and self_exempt(path):
            continue                       # emkeel's bespoke hand-maintained source — not a template/skill
        committed = _origin_or_local(path)
        if default:
            if (committed or "") != content:
                drift.append(path)
        elif committed is not None and committed != content:
            drift.append(path)
    # Append manifests (.gitignore/.gitattributes) drift when emkeel's line isn't present yet — the SAME
    # set `init` would deliver, so `update`/`doctor` must verify it too (not just _files + MERGE_FILES).
    for path, line in APPEND_LINES.items():
        content = _origin_or_local(path)
        if content is None or line not in content.splitlines():
            drift.append(path)
    # Merge files (e.g. .claude/settings.json) drift when the emkeel hook isn't wired in yet.
    for path, fn in MERGE_FILES.items():
        if fn(_origin_or_local(path)) is not None:        # would inject → not present → drift
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
        rc = ship_update(target)
        if rc == 0:
            _handoff_to_connect(target)
        return rc

    # --no-ship: refresh the LOCAL working tree (you commit it yourself).
    from emkeel.init import APPEND_LINES, MERGE_FILES, _files
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
    for path, fn in MERGE_FILES.items():
        p = target / path
        merged = fn(p.read_text(encoding="utf-8") if p.is_file() else None)
        if merged is None:
            results.append(("unchanged", path))
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(merged, encoding="utf-8")
        results.append(("merged", path))

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
    _handoff_to_connect(target)
    return 0


def _handoff_to_connect(target: Path) -> None:
    """After update delivers the wiring, if NEW config is still pending (the scoped local credential is
    missing), hand off to the next step explicitly — the user knows WHICH command and WHICH variables."""
    envp = target / ".env"
    if not (envp.is_file() and "GH_TOKEN" in envp.read_text(encoding="utf-8", errors="replace")):
        print("\n  → next / ahora: run `emkeel connect` to set the new config — GH_TOKEN (a fine-grained "
              "PAT scoped to this repo)  ·  corre `emkeel connect` para configurar: GH_TOKEN scopeado")


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
