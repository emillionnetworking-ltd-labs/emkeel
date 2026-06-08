# KEEL-38 — Wizard new-project: next steps must create + push the GitHub repo

## Context
In "new project" mode the wizard's next steps skipped creating/pushing the GitHub repo and
jumped to the connect steps (secrets), which need the repo to already exist on GitHub. That
left a gap: a brand-new project has no remote yet.

## Plan
- `src/emkeel/wizard.py` — for a new project, add a first next-step:
  `gh repo create <repo> --private --source=. --push`, before the connect steps. `tests/test_wizard.py`.
  Bump 0.1.22. (Network automation of push/PR/branch-protection is deferred to the AI-interpreter, KEEL-34.)

## Acceptance Criteria
- For a new project, the wizard's next steps include `gh repo create … --push` before secrets.
- For an existing repo, the next steps still show push + PR (unchanged).

## Anti-regression
- Test asserts next_steps for a new project contains the create-and-push command.
