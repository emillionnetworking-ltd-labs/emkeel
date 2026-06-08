# KEEL-42 — emkeel connect (automate the GitHub side via gh)

## Context
If `gh` is available, the GitHub-side setup (branch protection, secrets, and for a new project
creating + pushing the repo) can be automated — leaving only the Jira token (created on
Atlassian) as a manual step. This shrinks the post-setup checklist to nearly one command.

## Plan
- `src/emkeel/connect.py` — `emkeel connect`: reads emkeel.toml; if gh authed:
  - **new project** (repo not on GitHub) → offer `gh repo create --private --source=. --push`
    (safe — a fresh repo has no hooks), then branch protection + secrets;
  - **existing repo** → branch protection (`gh api PUT …/protection`, require `gates` + PR) +
    secrets (`gh secret set`, token via hidden prompt — never in chat).
  - Each action is confirmed; `--dry-run` prints the gh commands; missing/unauth gh → guidance.
- `src/emkeel/cli.py` dispatch `connect`. `tests/test_connect.py`. Bump 0.1.26.
- Pushing the *existing-repo* adopt branch stays manual (a pre-push hook could hang) — that's
  the AI-interpreter's job (KEEL-34), not a deterministic command.

## Acceptance Criteria
- `emkeel connect` sets branch protection (require `gates` + PR) and the Jira secrets via gh.
- For a new project (repo not on GitHub), it offers to create + push the repo first.
- The Jira token is read from a hidden prompt, never echoed or passed through a chat.
- `--dry-run` prints the gh commands and runs nothing; no emkeel.toml → tells the user to run setup.

## Anti-regression
- Tests cover: load_config, protection_body, gh helpers, dry-run (no calls), existing-repo flow
  (protection + secrets), and new-repo flow (create + push).
