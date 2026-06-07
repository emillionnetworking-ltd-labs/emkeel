# AI-assisted onboarding (agent playbook)

This file is read by a coding agent (Claude Code, Cursor, Copilot, …) to set Emkeel up in
the user's repo, conversationally.

> **Language:** converse with the user in **their** language (detect it from the chat).
> Produce all committed files/artifacts in **English**.

Legend: 🤖 = the agent does it · 👤 = the user does it (give them the exact link in chat,
one step at a time, and wait for confirmation).

## Step 0 — Gather details
Try to **derive** these from the repo first (git remote → `OWNER/REPO`; recent commit keys →
Jira project; an existing `emkeel.toml`), and only **ask** for what's missing. Confirm with
the user (in their language): **existing repo, or a new project from scratch?**

## Step 1A — Existing repo
- 🤖 **Create a branch first — never work on `main`:**
  `git checkout -b chore/<KEY>-adopt-emkeel` (use a real Jira KEY so the setup PR passes its
  own ticket-link gate).
- 🤖 Run `emkeel init . --github-repo … --jira-url … --jira-project … --dry-run`, show the
  plan, then run it for real (non-clobbering).
- 🤖 **Stage ONLY the files emkeel created** (plus the `.gitattributes`/`.gitignore` edits) —
  **never `git add -A`** (that sweeps in unrelated untracked files). Commit and push the branch.
- 🤖 Do **not** make the `gates` check required yet — don't break their current CI; adopt gradually.

## Step 1B — New project
🤖 `mkdir` + `git init`, then `emkeel init . …`, commit, and create the GitHub repo (private).

## Step 2 — Connect (the user does these; you only relay links)
> 🔒 **Security — never handle secrets.** Never ask the user to paste a token/password into
> this chat, and never write a secret value into any file. The user enters secrets **directly**
> in GitHub's encrypted **Secrets** UI (or a gitignored `.env`). You relay only the links and
> the secret **names**.

The output of `emkeel init` lists these links computed for the repo — relay them one at a time:
- 👤 1. Create a Jira API token — https://id.atlassian.net/manage-profile/security/api-tokens
- 👤 2. Add repo secrets `JIRA_BASE_URL` / `JIRA_EMAIL` / `JIRA_TOKEN` —
  `https://github.com/OWNER/REPO/settings/secrets/actions/new`
- 👤 3. Branch protection on `main` (require the `gates` check + a PR) —
  `https://github.com/OWNER/REPO/settings/branches`
- 👤 4. (optional) GitHub for Jira app — https://github.com/marketplace/jira-software-github

## Step 3 — Verify
🤖 Open a small PR from the branch; confirm the `gates` check runs and explain the result.
👤 Approve + merge. 🤖 Confirm the linked ticket moved to Done.

## Rules
- **Work on a branch + PR — never commit to `main`.** Stage **only** emkeel's files (no `git add -A`).
- **Never put secrets in this chat or in a committed file** — the user sets them in GitHub Secrets/`.env`.
- One install method only. Committed artifacts in English; the conversation in the user's language.
- One step at a time; wait for the user before moving on.
