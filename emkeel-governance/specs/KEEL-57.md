# KEEL-57 — emkeel update (refresh generated wiring to the installed version)

## Context
New adoptions get the latest templates automatically, but an already-adopted repo is frozen at its
adoption version: `pipx upgrade` updates the tool, not the repo's already-written files (AGENTS.md,
CLAUDE.md, workflows). So template/playbook improvements never reach existing repos — and editing
those files by hand is exactly the user-error we want to avoid.

## Plan
- `src/emkeel/update.py` — `emkeel update`: read `emkeel.toml` → `apply(..., force=True)` to
  re-write the generated wiring with the current templates (values preserved; `emkeel-governance/`
  and the user's `.gitignore` untouched). `src/emkeel/cli.py` dispatch `update`. `tests/test_update.py`.
  Bump 0.1.43.

## Acceptance Criteria
- `emkeel update` reads emkeel.toml and refreshes the generated wiring to the installed version,
  preserving the user's values and emkeel-governance/ artifacts.
- No emkeel.toml → tells the user to run `emkeel setup` first.

## Anti-regression
- Tests: load_cfg reads emkeel.toml; update refreshes a stale AGENTS.md (gains the onboard rule) and
  leaves emkeel-governance/ artifacts untouched; missing toml → exit 1 with guidance.
