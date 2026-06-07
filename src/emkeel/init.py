"""emkeel init — scaffold a target repo to be governed by Emkeel.

Idempotent and non-clobbering: existing files are reported "skip-exists" and left
untouched (use --force to overwrite), EXCEPT .gitattributes/.gitignore which get a
missing line appended. Secrets are NEVER written — only `.env.example` (a template).

CLI:  python -m emkeel.init [TARGET] --jira-url URL --jira-project KEY --github-repo OWNER/REPO
      [--emkeel-source SRC] [--dry-run] [--force]

--emkeel-source is what the generated CI runs as `pip install <SRC>`. Default "emkeel"
(works once published). For a PRIVATE emkeel, pass a git+token form, e.g.:
  'git+https://x-access-token:${EMKEEL_INSTALL_TOKEN}@github.com/OWNER/emkeel.git'
and add EMKEEL_INSTALL_TOKEN as a repo Actions secret.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path


def _default_source() -> str:
    """A version-PINNED default install spec so a new emkeel release never breaks an
    existing governed repo until it opts in. 0.x pins the minor; >=1.0 pins the major."""
    from emkeel import __version__

    major, minor = (int(x) for x in __version__.split(".")[:2])
    return f"emkeel~=0.{minor}.0" if major == 0 else f"emkeel~={major}.0"


@dataclass
class Config:
    jira_url: str = ""
    jira_project: str = ""
    github_repo: str = ""
    emkeel_source: str = field(default_factory=_default_source)


@dataclass
class Action:
    path: str
    kind: str  # "create" | "skip-exists" | "append" | "append-skip"


def _files(cfg: Config) -> dict[str, str]:
    return {
        "emkeel-governance/specs/.gitkeep": "",
        "emkeel-governance/adr/.gitkeep": "",
        "emkeel-governance/records/.gitkeep": "",
        ".github/workflows/emkeel-ci.yml": _ci_yaml(cfg.emkeel_source),
        ".github/workflows/jira-transition.yml": _jira_yaml(cfg.emkeel_source),
        "emkeel.toml": _toml(cfg),
        ".env.example": _env_example(),
        "AGENTS.md": _agents_md(),
    }


# Files where we append a single missing line (never clobber the rest).
APPEND_LINES = {
    ".gitattributes": "emkeel-governance/ export-ignore",
    ".gitignore": ".env",
}


def plan(target: Path, cfg: Config, force: bool) -> list[Action]:
    actions: list[Action] = []
    for rel in _files(cfg):
        exists = (target / rel).exists()
        actions.append(Action(rel, "create" if (force or not exists) else "skip-exists"))
    for rel, line in APPEND_LINES.items():
        p = target / rel
        present = p.exists() and line in p.read_text(encoding="utf-8").splitlines()
        actions.append(Action(rel, "append-skip" if present else "append"))
    return actions


def apply(target: Path, cfg: Config, force: bool, dry_run: bool) -> list[Action]:
    actions = plan(target, cfg, force)
    if dry_run:
        return actions
    files = _files(cfg)
    for a in actions:
        p = target / a.path
        if a.kind == "create":
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(files[a.path], encoding="utf-8")
        elif a.kind == "append":
            p.parent.mkdir(parents=True, exist_ok=True)
            prev = p.read_text(encoding="utf-8") if p.exists() else ""
            sep = "" if (prev == "" or prev.endswith("\n")) else "\n"
            p.write_text(prev + sep + APPEND_LINES[a.path] + "\n", encoding="utf-8")
    return actions


# --- templates -------------------------------------------------------------

def _toml(cfg: Config) -> str:
    return (
        "# Emkeel config (non-secret). Real credentials go in .env / GitHub Secrets.\n"
        "[jira]\n"
        f'base_url = "{cfg.jira_url}"\n'
        f'project_key = "{cfg.jira_project}"\n\n'
        "[github]\n"
        f'repo = "{cfg.github_repo}"\n\n'
        "[emkeel]\n"
        f'source = "{cfg.emkeel_source}"\n'
    )


def _env_example() -> str:
    return (
        "# Emkeel — Jira credentials. Copy to .env (gitignored) or set as GitHub Secrets.\n"
        "# NEVER commit the real values.\n"
        "JIRA_EMAIL=you@example.com\n"
        "JIRA_TOKEN=your-atlassian-api-token\n"
    )


def _ci_yaml(source: str) -> str:
    return f"""name: emkeel-ci

on:
  pull_request:
  push:
    branches: [main]

jobs:
  gates:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install emkeel
        run: pip install "{source}"
      - name: "Gate - ticket link"
        if: github.event_name == 'pull_request'
        env:
          EMKEEL_BRANCH: ${{{{ github.head_ref }}}}
          EMKEEL_PR_TITLE: ${{{{ github.event.pull_request.title }}}}
        run: python -m emkeel.gates.check_ticket_link
      - name: "Gate - plan present (features)"
        if: github.event_name == 'pull_request'
        env:
          EMKEEL_BRANCH: ${{{{ github.head_ref }}}}
        run: python -m emkeel.gates.check_plan_present
      - name: "Gate - acceptance criteria (features)"
        if: github.event_name == 'pull_request'
        env:
          EMKEEL_BRANCH: ${{{{ github.head_ref }}}}
        run: python -m emkeel.gates.check_acceptance_criteria
"""


def _jira_yaml(source: str) -> str:
    return f"""name: jira-transition

# Post-merge automation (NOT a gate): when a PR merges, move its linked ticket to Done.
on:
  pull_request:
    types: [closed]

jobs:
  transition:
    if: github.event.pull_request.merged == true
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install emkeel
        run: pip install "{source}"
      - name: Transition linked ticket to Done
        continue-on-error: true
        env:
          JIRA_BASE_URL: ${{{{ secrets.JIRA_BASE_URL }}}}
          JIRA_EMAIL: ${{{{ secrets.JIRA_EMAIL }}}}
          JIRA_TOKEN: ${{{{ secrets.JIRA_TOKEN }}}}
          EMKEEL_BRANCH: ${{{{ github.head_ref }}}}
          EMKEEL_PR_TITLE: ${{{{ github.event.pull_request.title }}}}
        run: python -m emkeel.jira
"""


def _agents_md() -> str:
    return """# AGENTS.md — this repo is governed by Emkeel

Rules that matter live in CI + branch protection, not here (this file is best-effort).

## Loop
1. One branch per ticket: `feat/<KEY-123>-slug` for features; `fix/`, `chore/`, `docs/` otherwise.
2. For `feat/` tickets: write `emkeel-governance/specs/<KEY>.md` with an "Acceptance Criteria" section.
3. Every bug fix starts with a failing test (permanent regression guard).
4. Open a PR. Merge requires: CI green + your approval + a linked ticket.

## Separation
- `emkeel-governance/` holds artifacts (specs/adr/records); it is `export-ignore` (never distributed).
"""


def connection_checklist(cfg: Config) -> str:
    repo = cfg.github_repo or "<owner>/<repo>"
    lines = [
        "NEXT — connect Emkeel (one-time):",
        "  1. GitHub for Jira app → install & link the repo so commits/PRs link to tickets.",
        f"  2. Branch protection on main of {repo}: require the 'gates' check + a PR.",
        "  3. Add JIRA_BASE_URL / JIRA_EMAIL / JIRA_TOKEN as GitHub Actions secrets.",
        "  4. Local: cp .env.example .env and fill it (it is gitignored).",
    ]
    if "EMKEEL_INSTALL_TOKEN" in cfg.emkeel_source:
        lines.append(
            "  5. Add EMKEEL_INSTALL_TOKEN secret (a fine-grained PAT with READ access to the "
            "emkeel repo) — the CI uses it to install the private package."
        )
    else:
        lines.append(
            "  5. Ensure the CI 'Install emkeel' source is reachable "
            f"(currently: pip install {cfg.emkeel_source})."
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    ap = argparse.ArgumentParser(prog="emkeel init", description="Scaffold a repo for Emkeel governance.")
    ap.add_argument("target", nargs="?", default=".", help="target repo path (default: .)")
    ap.add_argument("--jira-url", default="")
    ap.add_argument("--jira-project", default="")
    ap.add_argument("--github-repo", default="")
    ap.add_argument("--emkeel-source", default=_default_source(),
                    help="pip install source for emkeel in CI (default: version-pinned)")
    ap.add_argument("--dry-run", action="store_true", help="write nothing; just print the plan")
    ap.add_argument("--force", action="store_true", help="overwrite existing files")
    ns = ap.parse_args(argv)

    cfg = Config(ns.jira_url, ns.jira_project, ns.github_repo, ns.emkeel_source)
    target = Path(ns.target)
    actions = apply(target, cfg, ns.force, ns.dry_run)

    label = "DRY-RUN (nothing written)" if ns.dry_run else "applied"
    print(f"emkeel init [{label}] -> {target}")
    for a in actions:
        print(f"  {a.kind:12} {a.path}")
    print()
    print(connection_checklist(cfg))
    return 0


if __name__ == "__main__":
    sys.exit(main())
