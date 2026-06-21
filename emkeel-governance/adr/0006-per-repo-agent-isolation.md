# 6. Per-repo agent isolation — fail-safe deny of cross-repo actions, distributed by emkeel

- Status: accepted
- Date: 2026-06-21
- Deciders: operator (EMillion Networking)
- Ticket: KEEL-90

## Context

VS Code's split into per-repo windows is **cosmetic**: an agent in repo X's window is not actually
confined to X. `gh -R other/repo`, the Jira REST API with another `project_key`, and absolute / `../`
paths all reach into other repos. This bit us: an agent in the **emkeel** window created an **ECO**
ticket and a cross-repo PR in **em-ecosystem**. Identity already exists per repo (`emkeel.toml`:
`[github] repo`, `[jira] project_key`) — but nothing enforced it.

We need enforcement at a layer the agent can't simply ignore, distributed by emkeel so every governed
repo inherits it, with one absolute constraint: **fail-safe**. A guard that over-denies *bricks* the
agent — far worse than the leak. So it must deny ONLY unambiguous crossings and allow everything else.

## Decision

Three layers, all in emkeel (inherited via `pip install emkeel`):

1. **A PreToolUse hook → `emkeel guard`** (`src/emkeel/isolation.py`). Claude Code calls it before every
   `Bash` and `Edit`/`Write`; it reads this repo's identity from `emkeel.toml` and the pure function
   `decide(tool_name, tool_input, cwd, identity)` returns deny ONLY for:
   - `gh … -R/--repo <other>`; `git push` to a *foreign* github URL (a named remote like `origin` is the
     repo's own → allowed);
   - `emkeel jira … --project <other>` / a `--project` that isn't this repo's `project_key`;
   - `cd` into, or `Edit`/`Write`/`Read` of, a **sibling repo** (a path resolving under the repo's parent
     directory but outside the repo — the `projects/<other>` layout); scratch paths like `/tmp` or `~` are
     never flagged;
   - **self-protection**: `Edit`/`Write` of `.claude/settings*`, `.claude/hooks/*`, `emkeel.toml` (an agent
     must not disable its own guard).
   Everything else is **allowed**. On a deny it emits the harness JSON
   (`permissionDecision: "deny"`); on allow it emits nothing; and on ANY internal error or missing
   identity it **allows** and exits 0 — it never blocks.

2. **Distribution via a JSON-merge** (`init.py` `MERGE_FILES`): emkeel injects its two hook entries into
   `.claude/settings.json` **without clobbering** the repo's own settings (parse → inject if absent →
   write; idempotent; an unparseable file is left untouched). This is a new, JSON-aware sibling of the
   line-based `APPEND_LINES` — reported as a new mechanism.

3. **CLI guards (defense in depth)**: `emkeel jira create`/transition refuse a project that isn't this
   repo's `project_key`, even when the CLI is called directly (not via the hook). And **emkeel now governs
   itself** — it ships its own `emkeel.toml` (`project_key = KEEL`, `repo = …/emkeel`), closing the exact
   window the agent crossed through.

## Consequences

- **The window boundary is enforced, not cosmetic**: a cross-repo `gh`/Jira/path action from the wrong
  window is denied by the hook, and a cross-project `emkeel jira` by the CLI guard too.
- **Fail-safe by construction**: only unambiguous sibling-repo / cross-`-R` / cross-`--project` actions are
  denied; ambiguous, in-repo, `/tmp`, `~`, and undecidable (no `emkeel.toml`, parse error) cases are
  allowed. The guard exits 0 even on internal errors, so it can never brick the agent.
- **Inherited by every governed repo** via PyPI; emkeel governs itself too.
- **Zero-dependency**: stdlib only (`tomllib`, `json`, `re`, `pathlib`). The decision logic is a pure
  function, unit-tested without a filesystem or network.
- **Known limits (deliberate, for fail-safe)**: "another repo" is detected as a sibling under the same
  parent directory — an absolute path to an unrelated repo elsewhere on disk isn't flagged; and the
  hook screens `Bash`/`Edit`/`Write` (not `Read`) by default, though `decide` supports `Read` for repos
  that opt in. Tightening these is a follow-on if a real crossing slips through; widening blindly would
  risk bricking, which this ADR ranks as the worse failure.
