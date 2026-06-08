"""emkeel update — refresh the generated wiring to the installed version.

New adoptions get the latest templates automatically; an already-adopted repo is frozen at its
adoption version (`pipx upgrade` updates the tool, not your repo's files). `emkeel update` reads
your `emkeel.toml` and re-applies the wiring (AGENTS.md, CLAUDE.md, workflows, .env.example) with
the current templates — your values and `emkeel-governance/` are preserved. No manual editing.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from emkeel.init import Config, apply


def load_cfg(target: Path) -> Config | None:
    p = target / "emkeel.toml"
    if not p.is_file():
        return None
    d = tomllib.loads(p.read_text(encoding="utf-8"))
    return Config(
        jira_url=d.get("jira", {}).get("base_url", ""),
        jira_project=d.get("jira", {}).get("project_key", ""),
        github_repo=d.get("github", {}).get("repo", ""),
    )


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
    actions = apply(target, cfg, force=True, dry_run=False)
    print("emkeel update — refreshed the wiring to this version:")
    for a in actions:
        print(f"  {a.kind:12} {a.path}")
    print("\n(your values + emkeel-governance/ are unchanged — commit the refreshed files)")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
