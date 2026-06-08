# KEEL-34 — Agent-interpreter: AI relays the deterministic wizard

## Context
Make the AI a front-end that **transcribes** Emkeel's deterministic engine — it never decides
governance. The guarantee isn't the AI's obedience (a playbook can't enforce that) — it's the
server-side gates + branch protection ("out of the agent's reach"). The AI just needs the engine's
canonical questions + a tight protocol.

## Plan
- `src/emkeel/wizard.py` — `questions_json(cwd)` + `emkeel setup --json`: emit the canonical
  questions (bilingual prompts) + derived defaults + the deterministic `apply`/`after` steps, so the
  AI presents EXACTLY Emkeel's questions (translated to any language) and never invents its own.
- `src/emkeel/_docs/onboarding.md` — rewrite the playbook: brief; translate to any language; read
  `setup --json`; call the engine (`emkeel init` + git); environment guide+resume; secrets typed by
  the USER (via `emkeel connect`, hidden) with the security why; resume via `emkeel doctor`; never act
  alone / never decide. Bump 0.1.39.

## Acceptance Criteria
- `emkeel setup --json` prints canonical questions (es/en prompts) + derived defaults + apply/after, non-interactively.
- The playbook instructs the AI to relay (not invent), keep secrets off-chat, be brief, resume via doctor.

## Anti-regression
- Tests: questions_json shape + derived values; `main(["--json"])` prints valid JSON without prompting.
