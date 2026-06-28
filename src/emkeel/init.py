"""emkeel init — scaffold a target repo to be governed by Emkeel.

Idempotent and non-clobbering: existing files are reported "skip-exists" and left
untouched (use --force to overwrite), EXCEPT .gitattributes/.gitignore which get a
missing line appended. `init` NEVER writes secrets — only the non-secret scaffold
(`.env.example`, `.envrc`). The SCOPED local credential (`.env`, gitignored + chmod
600) is written by `emkeel connect` from a hidden paste (see ADR-0007).

CLI:  python -m emkeel.init [TARGET] --jira-url URL --jira-project KEY --github-repo OWNER/REPO
      [--emkeel-source SRC] [--dry-run] [--force]

--emkeel-source is what the generated CI runs as `pip install <SRC>`. Default: the PyPI
package, version-pinned (`emkeel~=X.Y.0`). For a PRIVATE fork, pass a git+token form, e.g.:
  'git+https://x-access-token:${EMKEEL_INSTALL_TOKEN}@github.com/OWNER/emkeel.git'
(then add EMKEEL_INSTALL_TOKEN as a repo Actions secret).
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path


def _default_source() -> str:
    """Default install spec: the PyPI package, version-pinned, so a new release never
    breaks an existing governed repo until it opts in. 0.x pins the minor; >=1.0 the major.
    (For a private fork, pass a git+token form via --emkeel-source.)"""
    from emkeel import __version__

    major, minor = (int(x) for x in __version__.split(".")[:2])
    return f"emkeel~=0.{minor}.0" if major == 0 else f"emkeel~={major}.0"


@dataclass
class Config:
    jira_url: str = ""
    jira_project: str = ""
    github_repo: str = ""
    emkeel_source: str = field(default_factory=_default_source)
    # Status-check contexts the repo declares MUST be required on the default branch (branch protection).
    # `emkeel doctor` checks these are enforced. Default = just emkeel's own `gates`; a repo with extra
    # CI gates (e.g. a security pipeline) lists them here so doctor catches "the check exists but isn't enforced".
    required_checks: list[str] = field(default_factory=lambda: ["gates"])


@dataclass
class Action:
    path: str
    kind: str  # "create" | "skip-exists" | "append" | "append-skip"


def _files(cfg: Config) -> dict[str, str]:
    return {
        "emkeel-governance/specs/.gitkeep": "",
        "emkeel-governance/adr/.gitkeep": "",
        "emkeel-governance/records/.gitkeep": "",
        "emkeel-governance/strategy/.gitkeep": "",
        ".github/workflows/emkeel-ci.yml": _ci_yaml(cfg.emkeel_source),
        ".github/workflows/jira-transition.yml": _jira_yaml(cfg.emkeel_source),
        "emkeel.toml": _toml(cfg),
        ".env.example": _env_example(),
        ".envrc": _envrc(),
        "AGENTS.md": _agents_md(),
        "CLAUDE.md": _claude_md(),
        ".claude/skills/strategy/SKILL.md": _strategy_skill(),
    }


# Files where we append a single missing line (never clobber the rest).
APPEND_LINES = {
    ".gitattributes": "emkeel-governance/ export-ignore",
    ".gitignore": ".env",
}

_GUARD_CMD = "emkeel guard"


def _guard_hook_block() -> list[dict]:
    """The emkeel isolation PreToolUse hooks: every Bash + Edit/Write call is screened by `emkeel guard`,
    which DENIES only unambiguous cross-repo actions (see emkeel.isolation)."""
    return [
        {"matcher": "Bash", "hooks": [{"type": "command", "command": _GUARD_CMD}]},
        {"matcher": "Edit|Write", "hooks": [{"type": "command", "command": _GUARD_CMD}]},
    ]


def _has_guard(pre) -> bool:
    for entry in pre if isinstance(pre, list) else []:
        for h in (entry.get("hooks", []) if isinstance(entry, dict) else []):
            cmd = (h.get("command", "") if isinstance(h, dict) else "") or ""
            if "emkeel guard" in cmd or "emkeel.isolation" in cmd:
                return True
    return False


def _settings_with_guard(existing: str | None) -> str | None:
    """Merge the emkeel isolation hook into a `.claude/settings.json` WITHOUT clobbering existing content.

    Returns the new JSON text, or None to LEAVE THE FILE UNTOUCHED — when the guard is already wired
    (idempotent) or the existing file is unparseable (never destroy a user's settings). This is the merge
    mechanism (a JSON-aware sibling of APPEND_LINES): emkeel injects only its hook entry, preserving the
    rest of the repo's own settings."""
    import json
    if existing is None or not existing.strip():
        data: dict = {}
    else:
        try:
            data = json.loads(existing)
        except (json.JSONDecodeError, ValueError):
            return None                                   # unparseable → don't clobber
    if not isinstance(data, dict):
        return None
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        return None
    pre = hooks.setdefault("PreToolUse", [])
    if not isinstance(pre, list) or _has_guard(pre):
        return None                                       # already wired → idempotent no-op
    pre.extend(_guard_hook_block())
    return json.dumps(data, indent=2) + "\n"


# Files emkeel MERGES into (JSON-aware, never clobbering): {path: merge_fn(existing|None)->new|None}.
MERGE_FILES = {".claude/settings.json": _settings_with_guard}

# The hand-maintained SOURCE files a CONSUMER gets as distributed wiring but emkeel's OWN repo authors by
# hand — emkeel has bespoke CI/docs (ci.yml/jira-transition.yml; its CLAUDE.md/AGENTS.md are the framework
# contract). Overwriting these in the emkeel repo would clobber the source, so they're skipped there.
# NOTE: this list is hand-maintained SOURCE only. GENERATED skills (no hand source) are NOT here — see
# `_is_generated_skill` / `self_exempt`: emkeel installs the skills it generates into its own repo too.
SELF_EXEMPT_WIRING = (
    ".github/workflows/emkeel-ci.yml",
    ".github/workflows/jira-transition.yml",
    "AGENTS.md",
    "CLAUDE.md",
)


def _is_generated_skill(rel: str) -> bool:
    """A generated, distributable skill under `.claude/skills/` — emkeel PRODUCES it (via `_strategy_skill`
    & friends) and keeps NO hand-maintained source to clobber. So it is installed in emkeel's OWN repo too,
    letting emkeel dogfood the very governance it ships (e.g. run `/strategy` in the emkeel window). This is
    the general rule: any skill emkeel generates self-installs, today `/strategy` and any future one."""
    return rel.startswith(".claude/skills/") and rel.endswith("SKILL.md")


def self_exempt(rel: str) -> bool:
    """Should `rel` be SKIPPED when emkeel applies its wiring to its OWN repo? Yes for the bespoke,
    hand-maintained source files emkeel must never clobber — but NEVER for a generated skill (it has no
    hand source, and emkeel needs it to run its own skills). The single rule shared by the ACTION (`plan`)
    and the DETECTION (`wiring_drift`) so they can never diverge."""
    return rel in SELF_EXEMPT_WIRING and not _is_generated_skill(rel)


def is_self_repo(target) -> bool:
    """True if `target` IS the emkeel package repo itself (not a consumer). Then the distributed wiring
    templates above don't apply. Detected by an explicit `self = true` marker in emkeel.toml, OR robustly
    by the repo shipping the emkeel package (pyproject `name = "emkeel"`). A generated consumer emkeel.toml
    has neither (`_toml()` never writes `self`), so consumers are unaffected."""
    import re as _re
    from pathlib import Path as _Path
    target = _Path(target)
    toml = target / "emkeel.toml"
    if toml.is_file() and _re.search(r'(?mi)^\s*self\s*=\s*true\b',
                                     toml.read_text(encoding="utf-8", errors="replace")):
        return True
    pp = target / "pyproject.toml"
    if pp.is_file() and _re.search(r'(?m)^\s*name\s*=\s*"emkeel"\s*$',
                                   pp.read_text(encoding="utf-8", errors="replace")):
        return True
    return False


def plan(target: Path, cfg: Config, force: bool) -> list[Action]:
    actions: list[Action] = []
    # SINGLE SOURCE OF TRUTH with wiring_drift: the ACTION (apply) exempts the SAME distributed wiring the
    # DETECTION (wiring_drift) does for the emkeel repo itself — so `emkeel update` can NEVER overwrite
    # emkeel's bespoke CI/docs (the KEEL-95 divergence that clobbered main; locked by a regression test).
    self_repo = is_self_repo(target)
    for rel in _files(cfg):
        if self_repo and self_exempt(rel):
            actions.append(Action(rel, "skip-self"))      # emkeel's own bespoke source — never written
            continue
        exists = (target / rel).exists()
        actions.append(Action(rel, "create" if (force or not exists) else "skip-exists"))
    for rel, line in APPEND_LINES.items():
        p = target / rel
        present = p.exists() and line in p.read_text(encoding="utf-8").splitlines()
        actions.append(Action(rel, "append-skip" if present else "append"))
    for rel, fn in MERGE_FILES.items():
        p = target / rel
        merged = fn(p.read_text(encoding="utf-8") if p.exists() else None)
        actions.append(Action(rel, "merge-skip" if merged is None else "merge"))
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
        elif a.kind == "merge":
            p.parent.mkdir(parents=True, exist_ok=True)
            merged = MERGE_FILES[a.path](p.read_text(encoding="utf-8") if p.exists() else None)
            if merged is not None:                        # None = nothing to do / don't clobber
                p.write_text(merged, encoding="utf-8")
    return actions


# --- templates -------------------------------------------------------------

def _toml(cfg: Config) -> str:
    from emkeel import __version__
    return (
        "# Emkeel config (non-secret). Real credentials go in .env / GitHub Secrets.\n"
        "[jira]\n"
        f'base_url = "{cfg.jira_url}"\n'
        f'project_key = "{cfg.jira_project}"\n\n'
        "[github]\n"
        f'repo = "{cfg.github_repo}"\n'
        "# required_checks: status-check contexts that MUST be required on the default branch.\n"
        "# `emkeel doctor` verifies they're enforced (catches \"the check exists but isn't required\").\n"
        "# `gates` is always checked. Add your other CI gates here, e.g.:\n"
        '# required_checks = ["gates", "Security Gate (All Checks)"]\n\n'
        "[emkeel]\n"
        f'source = "{cfg.emkeel_source}"\n'
        f'generated_with = "{__version__}"   # the Emkeel version that wrote this wiring (emkeel doctor checks it)\n'
    )


def _env_example() -> str:
    return (
        "# Emkeel — per-repo SCOPED credentials. Copy to .env (gitignored, chmod 600); NEVER commit real values.\n"
        "# `emkeel connect` writes .env for you (hidden paste). Activate per-repo loading: `direnv allow` (or `source .envrc`).\n"
        "# GH_TOKEN: a GitHub fine-grained PAT scoped to THIS repo (Contents RW, Pull requests RW, Metadata R).\n"
        "GH_TOKEN=github_pat_scoped_to_THIS_repo\n"
        "JIRA_BASE_URL=https://you.atlassian.net\n"
        "JIRA_EMAIL=you@example.com\n"
        "JIRA_TOKEN=your-atlassian-api-token\n"
    )


def _envrc() -> str:
    """Per-repo env loader. Plain bash (direnv runs it; also `source`-able by hand) → exports this repo's
    .env so its scoped creds live ONLY in this window. Non-secret (it just loads .env) → committed."""
    return (
        "# emkeel — per-repo environment. Run `direnv allow` once to auto-load on `cd` into this repo\n"
        "# (or `source .envrc` manually). Loads .env (gitignored, chmod 600): GH_TOKEN + JIRA_* scoped to\n"
        "# THIS repo, so an agent in this window can't reach another repo's GitHub/Jira.\n"
        "if [ -f .env ]; then set -a; . ./.env; set +a; fi\n"
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
        with:
          fetch-depth: 0          # full history so check_maint_scope can diff against the base
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
          # Secrets let the gate verify the ticket EXISTS in Jira (404 -> hard fail). Absent -> syntax-only warning.
          JIRA_BASE_URL: ${{{{ secrets.JIRA_BASE_URL }}}}
          JIRA_EMAIL: ${{{{ secrets.JIRA_EMAIL }}}}
          JIRA_TOKEN: ${{{{ secrets.JIRA_TOKEN }}}}
        run: python -m emkeel.gates.check_ticket_link
      - name: "Gate - ticket precedes work (ticket-first)"
        if: github.event_name == 'pull_request'
        env:
          EMKEEL_BRANCH: ${{{{ github.head_ref }}}}
          EMKEEL_PR_TITLE: ${{{{ github.event.pull_request.title }}}}
          EMKEEL_BASE_REF: ${{{{ github.base_ref }}}}
          # Compares Jira's `created` to the branch's first commit (ticket-first). Secrets absent -> inconclusive warning.
          JIRA_BASE_URL: ${{{{ secrets.JIRA_BASE_URL }}}}
          JIRA_EMAIL: ${{{{ secrets.JIRA_EMAIL }}}}
          JIRA_TOKEN: ${{{{ secrets.JIRA_TOKEN }}}}
        run: python -m emkeel.gates.check_ticket_precedes_work
      - name: "Gate - ticket placed (decide the sprint before merge)"
        if: github.event_name == 'pull_request'
        env:
          EMKEEL_BRANCH: ${{{{ github.head_ref }}}}
          EMKEEL_PR_TITLE: ${{{{ github.event.pull_request.title }}}}
          # Blocks merge while a sprint-project ticket is still pending a placement decision. Secrets absent -> inconclusive.
          JIRA_BASE_URL: ${{{{ secrets.JIRA_BASE_URL }}}}
          JIRA_EMAIL: ${{{{ secrets.JIRA_EMAIL }}}}
          JIRA_TOKEN: ${{{{ secrets.JIRA_TOKEN }}}}
        run: python -m emkeel.gates.check_ticket_placed
      - name: "Gate - maintenance scope (emkeel-maint lane only)"
        if: github.event_name == 'pull_request'
        env:
          EMKEEL_BRANCH: ${{{{ github.head_ref }}}}
          EMKEEL_BASE_REF: ${{{{ github.base_ref }}}}
        run: python -m emkeel.gates.check_maint_scope
      - name: "Gate - dependabot scope (dependabot lane only)"
        if: github.event_name == 'pull_request'
        env:
          EMKEEL_BRANCH: ${{{{ github.head_ref }}}}
          EMKEEL_BASE_REF: ${{{{ github.base_ref }}}}
        run: python -m emkeel.gates.check_dependabot_scope
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
      - name: "Gate - strategy link (features; dormant until a strategy exists)"
        if: github.event_name == 'pull_request'
        env:
          EMKEEL_BRANCH: ${{{{ github.head_ref }}}}
        run: python -m emkeel.gates.check_strategy_link
      - name: "Gate - strategy quality (every strategy doc is sourced + complete)"
        if: github.event_name == 'pull_request'
        run: python -m emkeel.gates.check_strategy_quality
      - name: "Gate - strategy change (north star only on a strategy/ lane)"
        if: github.event_name == 'pull_request'
        env:
          EMKEEL_BRANCH: ${{{{ github.head_ref }}}}
          EMKEEL_BASE_REF: ${{{{ github.base_ref }}}}
        run: python -m emkeel.gates.check_strategy_change
      - name: "Gate - strategy process (non-skippable steps: <topic>.process.json >= validated + provenance)"
        if: github.event_name == 'pull_request'
        env:
          EMKEEL_BASE_REF: ${{{{ github.base_ref }}}}
        run: python -m emkeel.gates.check_strategy_process
      - name: "Gate - critical change needs an integration test (tests/integration/)"
        if: github.event_name == 'pull_request'
        env:
          EMKEEL_BASE_REF: ${{{{ github.base_ref }}}}
        run: python -m emkeel.gates.check_critical_integration
      - name: "Gate - governance-doc conventions (canonical English fields + bidirectional ADR supersession)"
        if: github.event_name == 'pull_request'
        run: python -m emkeel.gates.check_doc_conventions
      - name: "Gate - strategy alignment (feature acknowledges the north star)"
        if: github.event_name == 'pull_request'
        env:
          EMKEEL_BRANCH: ${{{{ github.head_ref }}}}
        run: python -m emkeel.gates.check_strategy_alignment
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
        # No blind continue-on-error: benign cases (already Done, secrets missing) succeed in code;
        # a REAL failure (404 / POST failed / status didn't land on Done) surfaces red via ::error::.
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

## How to respond
Communicate like an engineer briefing the team: short and non-repetitive, without dropping context that changes the decision.
- Give the needed context first, briefly. Facts, results, or steps → a list, one per line. Reasoning → a short paragraph. Never chain separate facts with ";" on one line.
- No repetition, no tangents, no re-explaining what's known.
- Default to a few lines of prose + a short list. Reserve tables and multi-header layouts for genuinely complex comparisons, not routine updates.
- Refusing or blocked by a guardrail? State the block and the one correct path in a few lines — don't re-justify a safe decision.
- Put the conclusion and your recommendation last, with the next step.

## When to act vs wait
Analysis and action are different modes — don't slide from one into the other.
- After an analysis, a diagnosis, or anything that is the operator's to decide, STOP at the conclusion + recommendation and WAIT for an explicit go-ahead before starting work (creating a ticket, a branch, a PR, or changing shared state).
- A clarification or a restated requirement is NOT approval to execute. When unsure whether "go" was given, ask — don't assume.
- When the operator has already said to proceed ("do it", "go ahead"), act without re-asking.

## Loop
1. One branch per ticket: `feat/<KEY-123>-slug` for features; `fix/`, `chore/`, `docs/` otherwise.
   **Create the ticket FIRST, then branch from its key, then write the code** — that order is not advice:
   `check_ticket_precedes_work` FAILS a PR whose ticket was created AFTER the branch's first commit
   (Jira's `created` vs the first commit's author-date). The easy, correct path is `emkeel start <summary>`
   — it creates the ticket and `git checkout -b <kind>/<KEY>-slug` in one step, so the order can't invert.
   The ticket is born in the project's INITIAL state — `emkeel jira create` has no `--status`; a ticket is
   never born `Done`. If creating it fails (creds, a cross-project block) it errors red and stops — do NOT
   proceed to open a PR without a ticket. Fix the cause (`emkeel connect`) and retry.
   When the project uses sprints, create ALWAYS recommends a placement and leaves the ticket PENDING — it
   does NOT auto-place it in a sprint: the ticket stays in the backlog (labeled `emkeel-placement-pending`)
   and the OPERATOR decides the sprint. RELAY the recommendation (the `::notice::` it prints) to the
   operator — surface it, don't swallow it — and let them choose; pass `--sprint <id>|active` to place it,
   or leave it in the backlog. The decision is not optional: `check_ticket_placed` BLOCKS the merge while a
   sprint-project ticket is still undecided. Decide it with `emkeel jira place <KEY> --sprint active|backlog|<id>`
   (it clears the pending flag), or place it in Jira. (`emkeel doctor` lists tickets still awaiting a decision.)
2. For `feat/` tickets: write `emkeel-governance/specs/<KEY>.md` with an "Acceptance Criteria" section.
3. Every bug fix starts with a failing test (permanent regression guard).
4. Open a PR. Merge requires: CI green + your approval + a linked ticket.
5. **`Done` is earned by the work + the merge** — move the ticket with `emkeel jira transition` after it
   merges, never at create. (Like a strategy's `approved`, a terminal state is never self-written up front.)

## Don't break something else in silence
- **Critical / cross-cutting change → add an INTEGRATION test.** If you touch creds, isolation, the
  distribution wiring, the agent contract, or a CI gate, add/extend a test under `tests/integration/`
  that exercises the affected flow end-to-end — not just a unit test. (The `check_critical_integration`
  gate enforces this; born from a creds change that silently broke ticket creation.)
- **Critical infra must be self-sufficient.** Don't depend on optional environment tools (e.g. `direnv`);
  read what you need directly (in-process) so the flow works on a bare machine.
- **Never hide failures with `2>/dev/null`** on a step that can fail, and **verify the `cwd`/destination
  before writing** — a silenced `cd` that failed once clobbered a real `.env`.

## Strategy (the north star — don't drift)
- A development strategy for an area lives in `emkeel-governance/strategy/<area>.md` (goal,
  architecture, parameters, non-goals). Created once, human-approved, committed.
- **Before working a feature, read the strategy it serves and align to it.** Declare it in the
  spec with a line `Strategy: <area>` (or `Strategy: none` for a deliberate standalone).
- When a spec declares `Strategy: <area>`, it must also carry an `## Alignment` section that lists
  which north-star decisions/constraints the feature implements or touches — the `check_strategy_alignment`
  gate requires it to exist and be non-empty (the human judges whether the content is true at the PR).
- Once any strategy exists, the `check_strategy_link` gate requires that line — so no feature
  merges without a conscious strategy decision.
- **Changing the north star is a deliberate act on its own lane.** A PR that creates, edits, or
  deletes a `strategy/*.md` MUST be on a `strategy/<KEY-123>-slug` branch (its own ticket,
  human-approved) — the `check_strategy_change` gate FAILS a `feat/`/`fix/` PR that touches it.
  Never drift the strategy silently inside a feature to make the code fit.

## Separation
- `emkeel-governance/` holds artifacts (specs/adr/records/strategy); it is `export-ignore` (never distributed).

## Documentation (docs/)
- `docs/` = product reference documentation (architecture, how-it-works) — human-facing, living.
  Governance (strategy/adr/specs/records) lives in `emkeel-governance/`, **never** in `docs/`.
- Specs that mirror the code (OpenAPI, data model) are **regenerated** from the source — don't
  hand-maintain a frozen snapshot (it drifts and misleads).
- `docs/archive/` holds preserved-but-inactive docs; each carries a header marking it historical.
- A dead doc → delete it (git history is the archive); don't keep a "to-delete-later" pile.
"""


def _claude_md() -> str:
    # AGENTS.md is the cross-tool canonical contract. Claude Code reads CLAUDE.md, so this
    # file just imports AGENTS.md (portable — a real file with an @import, not a symlink).
    return (
        "# This repo is governed by Emkeel. The agent contract is AGENTS.md.\n"
        "# Claude Code reads CLAUDE.md, so AGENTS.md is imported below:\n"
        "@AGENTS.md\n"
    )


def _strategy_skill() -> str:
    # NOT skippable prose: this skill DRIVES the governed-process engine (emkeel.process). After each step's
    # real work you record it with `emkeel strategy advance <step> <topic> --set <evidence>`; the engine
    # REFUSES to advance out of order or without the evidence, and a CI gate (check_strategy_process)
    # fails any PR whose committed <topic>.process.json hasn't reached `validated` (reality evidence) with
    # real research provenance — a strategy can pass every process step and still be wrong.
    return """---
name: strategy
description: >
  Research and decide a development/engineering strategy for a topic (a module, security, a
  technology choice, an approach…). Produces a grounded, sourced strategy doc, driven through
  emkeel's governed-process engine — the steps are NON-SKIPPABLE. Use when you must choose the
  right path and want it researched, not guessed.
---

# /strategy <topic>

Produce a RESEARCHED strategy for `<topic>`, persisted at `emkeel-governance/strategy/<topic>.md`.
**Every claim must cite a real source (file:line in the repo, or a URL) gathered with TOOLS — never
from memory. Never invent an option or a source.**

This skill is a state machine, not advisory prose. After each step's real work, record it with
`emkeel strategy advance <step> <topic> --set <evidence>` — the engine REFUSES an out-of-order or
evidence-less advance (exit 1), and CI (`check_strategy_process`) fails the PR unless the committed
`<topic>.process.json` reached `validated` (the strategy was tried on a real case) with real research
provenance. `emkeel strategy status <topic>` shows where you are. Run each `advance` ONLY after that step's
work is done.

1. **Scaffold** — `emkeel strategy new <topic>` creates the structured doc; declare up front the
   **kill-criteria** (what would prove this strategy WRONG — the conditions under which to abandon it):
   `emkeel strategy advance scaffolded <topic> --set=topic=<topic> --set='kill_criteria=[<cond1>,<cond2>,…]'`
2. **Research** (ground in reality; fan out with subagents):
   - *Repo:* Read/Grep the actual code & config for `<topic>` — what exists, conventions, constraints. Cite `file:line`.
   - *Market:* WebSearch/fetch real options & trade-offs. Cite URLs.
   Record the provenance — the engine and CI REFUSE `researched` without it:
   `emkeel strategy advance researched <topic> --set='sources=[<url>,<file:line>,…]'`
   If `<topic>` genuinely has no market/external dimension, declare it EXPLICITLY (never skip the web silently):
   `emkeel strategy advance researched <topic> --set=internal_only=true`
3. **Propose** — fill the Options table with **≥2 real options**, each with its **Source**, pros, cons, risk:
   `emkeel strategy advance proposed <topic> --set='options=[<opt1>,<opt2>,…]'`
4. **Critique** — a multi-lens adversarial PANEL (fan out subagents, one per angle): re-open each option's
   cited source (does it really say that?) AND attack from DISTINCT lenses — recommended: discovery/SEO,
   professional completeness, calibration to the real case, legal/compliance, plus any topic-specific angle.
   Then a **completeness critic**: what dimension is missing? Record ONE finding per lens + the completeness
   answer (the engine refuses a one-liner; CI requires ≥3 distinct lenses unless the doc declares `Impact: low`):
   `emkeel strategy advance critiqued <topic> --set lens_discovery="…" --set lens_completeness="…" --set lens_calibration="…" --set lens_legal="…" --set completeness="<what's missing, or 'none'>"`
5. **Check** — run `emkeel strategy check <topic>` and fix until it passes (green = sourced + complete). Then:
   `emkeel strategy advance checked <topic> --set=check_passed=true`
6. **Validate against reality** — apply the recommendation to ONE real case (cheap is fine: try it once and
   look at the result). Record the case, how you tested it, the **outcome** (`pass` | `fail` | `mixed`), and a
   **resolvable proof** (a repo `file:line`, a URL, or an external citation). The engine and CI REFUSE
   `validated` without it — reality is non-skippable, and a `fail`/`mixed` is an HONEST record, never hidden:
   `emkeel strategy advance validated <topic> --set=case="<the real case>" --set=method="<how you tested>" --set=outcome=<pass|fail|mixed> --set=evidence_ref=<file:line|URL>`
7. **Human gate — present** — present the options + your recommendation to the operator. **Do NOT decide
   for them.** Record that you showed it (this does NOT approve anything) — the LAST step you commit in the
   lane PR. If the reality outcome was `fail`/`mixed`, proceeding requires a recorded `proceed_justification`
   — approving despite a failed reality test must be a deliberate, on-record act:
   `emkeel strategy advance presented <topic> --set=presented_to=<operator>`
   (add `--set=proceed_justification="<why proceed despite the reality result>"` when the outcome was not `pass`)
8. **Approval is the MERGE — never stamp it yourself.** The operator approves by **approving + merging the
   PR** (branch protection requires a human approving review). Do NOT run `emkeel strategy advance approved`
   in the lane PR — a self-written `approved_by` certifies nothing, and the `check_strategy_process` gate
   FAILS a committed `approved` (the merge hasn't happened yet). The committed `<topic>.process.json` stops
   at `presented`; the merge IS the approval, recorded immutably in the PR/git history.
   On the operator's yes, set `Status: APPROVED` in the doc, finalize the Recommendation, offer to record
   the decision as an ADR in `emkeel-governance/adr/`, and remind them to add `Strategy: <topic>` to
   feature specs (the `check_strategy_link` gate enforces it).

**Refining an existing strategy?** A new refinement (a new ticket on the same `<topic>`) starts the process
CLEAN — re-run from `scaffolded`; the engine resets and a prior refinement's `approved` NEVER carries over.

**Retiring a strategy?** A path that didn't work can be withdrawn: in a `strategy/<KEY>-slug` lane (with a
ticket), DELETE `<topic>.md` AND its `<topic>.process.json` together — as a pair. The gate accepts a clean
retiro; deleting the doc while leaving the sidecar (or vice versa) is an orphan → FAIL.

**Commit `emkeel-governance/strategy/<topic>.process.json` alongside the doc** — it is the proof the steps
ran, and CI reads it. `emkeel strategy status <topic>` shows ✓/· per step. Never skip the human gate
(presenting + the merge are the operator's). Never cite a source you didn't open.
"""


def connection_checklist(cfg: Config) -> str:
    repo = cfg.github_repo or "<owner>/<repo>"
    jira = cfg.jira_url or "https://your.atlassian.net"
    base = f"https://github.com/{repo}"
    lines = [
        "NEXT — connect Emkeel (one-time). Steps you do, with the exact links:",
        "",
        "  1. Create a Jira API token:",
        "     https://id.atlassian.net/manage-profile/security/api-tokens",
        "",
        f"  2. Add repo Actions secrets:  {base}/settings/secrets/actions/new",
        f"       JIRA_BASE_URL = {jira}",
        "       JIRA_EMAIL    = <your Atlassian email>",
        "       JIRA_TOKEN    = <the token from step 1>",
        "",
        "  3. Branch protection on 'main' (require the 'gates' check + a PR):",
        f"     {base}/settings/branches",
        "     (Declaring extra CI gates in emkeel.toml `required_checks` makes `emkeel doctor`",
        "      verify each one is actually enforced — not just present.)",
        "",
        "  4. (optional) GitHub for Jira app (links commits/PRs to tickets):",
        "     https://github.com/marketplace/jira-software-github",
    ]
    if "EMKEEL_INSTALL_TOKEN" in cfg.emkeel_source:
        lines += [
            "",
            f"  5. Private fork only — add the EMKEEL_INSTALL_TOKEN secret:  {base}/settings/secrets/actions/new",
            "       (a fine-grained PAT with READ access to your emkeel fork)",
        ]
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
