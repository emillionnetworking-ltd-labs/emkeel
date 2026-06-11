# KEEL-73 — Scaffold the thin /strategy skill into adopted repos

## Context
Layer 2 shell. The reliability lives in the tested Python (`emkeel strategy new`/`check`); the skill
is a thin prose orchestrator that calls them + drives grounded research + the human gate.

## Plan
- `src/emkeel/init.py` — `_strategy_skill()` (frontmatter + playbook: scaffold → grounded research
  with tools (not memory) via subagents → sourced Options → adversarial critic re-verifies sources →
  `strategy check` → human gate → APPROVE/optional ADR). Add `.claude/skills/strategy/SKILL.md` to
  `_files` so init/update scaffold it. `tests/test_init.py`. Bump 0.1.59.

## Acceptance Criteria
- Adopting/updating emkeel scaffolds `.claude/skills/strategy/SKILL.md`; the skill references the
  tested CLI commands and states the anti-hallucination rules (tools-not-memory, human gate).

## Anti-regression
- Test: apply scaffolds the strategy skill with the CLI references + the key rules.
