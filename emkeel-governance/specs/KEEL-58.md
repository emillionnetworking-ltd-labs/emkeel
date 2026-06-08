# KEEL-58 — Remove the AI onboarding (keep the deterministic wizard)

## Context
The AI-assisted onboarding got lost in practice (the agent drifts). Keep the tested deterministic
wizard/manual path; defer the AI experience to a future VS Code plugin. Remove all AI-onboarding
scaffolding so there's no half-working AI path shipped.

## Plan
- Remove `emkeel onboard` (cli.py command + `src/emkeel/_docs/onboarding.md`).
- Remove `emkeel setup --json` (`questions_json`) and `emkeel eject --json` (`eject_json`).
- Remove the `AGENTS.md` "run `emkeel onboard` first" rule from `init.py`.
- Remove the README `emkeel onboard` row (keep "AI-assisted teams" positioning + "agent's reach").
- Remove the related tests. Bump 0.1.44.

## Acceptance Criteria
- `emkeel onboard` and the `--json` flags no longer exist; the usage line lists no `onboard`.
- The generated AGENTS.md no longer mentions onboard; the deterministic wizard/manual path is unchanged.

## Anti-regression
- The full suite passes with the AI-onboarding tests removed; the wizard/connect/eject/sync/update/doctor flows are intact.
