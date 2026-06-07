# AI-assisted onboarding (agent playbook)

This file is read by a coding agent (Claude Code, Cursor, Copilot, …) to set Emkeel up in
the user's repo, conversationally.

> **Language:** converse with the user in **their** language (detect it from the chat).
> Produce all committed files/artifacts in **English**.

Legend: 🤖 = the agent does it · 👤 = the user does it (give them the exact link in chat,
one step at a time, and wait for confirmation).

## Step 0 — Ask the scenario
Ask the user (in their language): **"Is this an existing repo, or a new project from scratch?"**
Also collect: GitHub `OWNER/REPO`, Jira base URL, and Jira project KEY.
- Existing repo → Step 1A · New project → Step 1B.

## Step 1A — Existing repo
🤖 In the repo, run `emkeel init . --github-repo … --jira-url … --jira-project … --dry-run`,
show the plan, then run it for real (non-clobbering). Do **not** make the `gates` check
required yet — don't break their current CI; adopt conventions gradually.

## Step 1B — New project
🤖 `mkdir` + `git init`, then `emkeel init . --github-repo … --jira-url … --jira-project …`.
Create the GitHub repo (private by default) and push the first commit.

## Step 2 — Connect (surface each link in chat, with exact values)
The output of `emkeel init` already lists these links computed for the repo — relay them
verbatim, one at a time:
- 👤 1. Create a Jira API token — https://id.atlassian.net/manage-profile/security/api-tokens
- 👤 2. Add repo secrets `JIRA_BASE_URL` / `JIRA_EMAIL` / `JIRA_TOKEN` —
  `https://github.com/OWNER/REPO/settings/secrets/actions/new`
- 👤 3. Branch protection on `main` (require the `gates` check + a PR) —
  `https://github.com/OWNER/REPO/settings/branches`
- 👤 4. (optional) GitHub for Jira app — https://github.com/marketplace/jira-software-github

## Step 3 — Verify
🤖 Open a small PR; confirm the `gates` check is green and explain the result.
👤 Approve + merge. 🤖 Confirm the linked ticket moved to Done.

## Rules
- Never write secret values into files — the user pastes them into GitHub secrets.
- Committed artifacts in English; the conversation in the user's language.
- One step at a time; wait for the user before moving on.
