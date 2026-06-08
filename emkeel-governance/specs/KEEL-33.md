# KEEL-33 — emkeel setup (interactive wizard)

## Context
The "paste a prose phrase to your AI" onboarding proved fragile and complex. A real install
wizard — interactive, deterministic, **no AI** — is simpler and can't be "talked out of" its
steps. `emkeel onboard` only printed a playbook for an AI; this adds a true wizard.

## Plan
- `src/emkeel/wizard.py` — interactive wizard: asks **language first** (es/en), then
  existing-vs-new and trial-vs-real; derives GitHub/Jira from the repo and confirms; does the
  local setup (branch+scaffold+commit for existing; `git init`+scaffold+commit for new); prints
  guided, trial-aware next steps. Reuses `emkeel.init`.
- `src/emkeel/cli.py` — dispatch `emkeel setup`.
- `tests/test_wizard.py`; README note (incl. `pipx run emkeel setup`).

## Acceptance Criteria
- `emkeel setup` runs an interactive wizard whose **first question is the language** (es/en).
- It derives GitHub repo + Jira (project/URL) from the repo and lets the user confirm/override.
- Existing repo: creates `chore/<KEY>-adopt-emkeel`, scaffolds, and commits **only** Emkeel's files.
- New project: runs `git init`, scaffolds, and commits.
- It prints clear, **trial-aware** next steps; in trial mode it does not push or set secrets.
- The wizard is deterministic Python (no AI), dispatched via `emkeel setup`.

## Anti-regression
- Tests cover: i18n + branch name, `derive_defaults` (in-repo and outside), plan lines,
  `run_setup` (existing + new), and a `main()` smoke run with scripted input.
