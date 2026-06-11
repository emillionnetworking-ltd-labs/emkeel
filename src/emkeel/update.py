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


def wiring_drift(target: Path) -> list[str]:
    """Generated files whose committed content differs from what the current Emkeel would write
    (i.e. `emkeel update` would change them). Excludes emkeel.toml (it carries a version stamp that
    always differs) and the append-only .gitignore/.gitattributes."""
    cfg = load_cfg(target)
    if cfg is None:
        return []
    from emkeel.init import _files
    drift = []
    for path, content in _files(cfg).items():
        if path == "emkeel.toml":
            continue
        p = target / path
        if p.is_file() and p.read_text(encoding="utf-8") != content:
            drift.append(path)
    return drift


def main(argv: list[str] | None = None) -> int:
    target = Path(".")
    cfg = load_cfg(target)
    if cfg is None or not cfg.github_repo:
        print("  No emkeel.toml here — run `emkeel setup` first.")
        return 1

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
    print("emkeel update — refreshed the wiring:")
    for s, p in changed:
        print(f"  {s:10} {p}")
    n_un = len(results) - len(changed)
    if n_un:
        print(f"  ({n_un} file(s) already current)")
    print("\n(your values + emkeel-governance/ are unchanged — commit the refreshed files)")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
