# KEEL-19 — Installer provides CLAUDE.md (Claude Code bridge)

## Context
A zero-knowledge user shouldn't need to know about agent-instruction files. `AGENTS.md` is
the cross-tool canonical contract (Cursor, Copilot, … read it), but Claude Code reads
`CLAUDE.md`. So `emkeel init` should also drop a `CLAUDE.md` that imports `AGENTS.md` —
portable (a real file with `@AGENTS.md`, not a symlink), non-clobbering.

## Plan
- `src/emkeel/init.py` — add `_claude_md()` (content: `@AGENTS.md`) and include `CLAUDE.md`
  in the scaffolded files.
- `tests/test_init.py` — assert CLAUDE.md is created and imports AGENTS.md.
- Bump 0.1.6.

## Acceptance Criteria
- `emkeel init` creates a `CLAUDE.md` whose content imports `AGENTS.md` (`@AGENTS.md`).
- `AGENTS.md` remains the canonical contract (unchanged); CLAUDE.md is only the Claude bridge.
- Non-clobber: an existing `CLAUDE.md`/`AGENTS.md` is skipped, not overwritten (unless `--force`).
- No secret is written; the wheel/sdist stay clean (no governance).

## Anti-regression
- Tests cover: CLAUDE.md is planned/created, and its content contains `@AGENTS.md`.
