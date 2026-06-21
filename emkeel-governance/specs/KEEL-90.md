# KEEL-90 — Per-repo agent isolation: deny cross-repo actions, distributed by emkeel

## Context
VS Code's per-repo windows are cosmetic — `gh -R other`, the Jira API with another `project_key`, and
absolute/`../` paths reach across repos. An agent in the **emkeel** window created an **ECO** ticket + a
cross-repo PR in **em-ecosystem**. Identity exists (`emkeel.toml`) but nothing enforced it. This forces
the isolation at a layer the agent can't skip, distributed by emkeel, **fail-safe** (over-denying bricks
the agent → deny only unambiguous crossings).

## Plan
1. **`src/emkeel/isolation.py`** — pure `decide(tool_name, tool_input, cwd, identity) → (allow|deny,
   reason)`; denies only: `gh -R/--repo <other>`, `git push` to a foreign URL, `--project <other>`,
   `cd`/`Edit`/`Write`/`Read` into a sibling repo, and `Edit`/`Write` of the guard config
   (`.claude/settings*`, `.claude/hooks/*`, `emkeel.toml`). Allows everything else. `find_identity` reads
   `emkeel.toml`. `emkeel guard` (entrypoint) reads the PreToolUse JSON on stdin, emits the harness deny
   JSON, and ALWAYS exits 0 (any error/no-identity → allow — never bricks).
2. **Distribution** — `init.py` `MERGE_FILES`: a JSON-aware merge that injects the two PreToolUse hook
   entries into `.claude/settings.json` without clobbering (idempotent; unparseable → untouched). New
   mechanism (sibling of `APPEND_LINES`); wired into `plan`/`apply`/`wiring_drift`/`managed_paths`.
3. **CLI guards (defense in depth)** — `emkeel jira create`/transition refuse a `--project`/ticket-key
   that isn't this repo's `project_key`. emkeel ships its **own `emkeel.toml`** (`KEEL`, `…/emkeel`) so it
   governs itself.
4. ADR `0006-per-repo-agent-isolation.md`. Bump 0.1.76.

## Acceptance Criteria
1. `decide` ALLOWS ordinary in-repo work (pytest, git push origin, gh pr create, `cd /tmp`, `cd ~`, edits
   in-repo) — fail-safe, never bricks.
2. `decide` DENIES: `gh -R <other>`, `--project <other>`, `git push <foreign-url>`, `cd ../<sibling>`,
   `Edit`/`Write`/`Read` of a sibling repo, and `Edit`/`Write` of the guard config.
3. No identity / parse error / internal error → ALLOW (the guard never blocks).
4. `emkeel guard` emits the deny JSON on a crossing and nothing on allow; always exit 0.
5. Distribution merges the hook into `.claude/settings.json` without clobbering existing settings
   (idempotent; unparseable left untouched).
6. CLI guard refuses a cross-project `emkeel jira`; emkeel governs itself (`emkeel.toml` present).

## Notes
- New distribution mechanism reported: `MERGE_FILES` (JSON merge), because the line-based `APPEND_LINES`
  can't inject a hook entry into a JSON object without clobbering.
