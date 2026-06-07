# AI-assisted onboarding (agent playbook)

This file is read by a coding agent (Claude Code, Cursor, Copilot, …) to set Emkeel up in
the user's repo, conversationally.

> **Golden rule:** treat the user as new to all of this. **Before every action, explain in
> plain language what you're about to do and why**, then do it and report the result. One step
> at a time; wait for the user's OK before continuing.
>
> **Language:** converse in the **user's** language. All committed files/artifacts in **English**.

Legend: 🤖 = you do it (narrate it first) · 👤 = the user does it (give them the exact link).

## Step 0 — Understand the situation
Briefly tell the user what Emkeel does (every change becomes a small PR with an automatic
check; merging can auto-close the Jira ticket). Then ask, in their language:
1. **"Is this an existing repo, or a brand-new project?"**
2. **"Is this a trial run to see how it works, or are you adopting Emkeel for real?"**

Derive the rest from the repo (git remote → `OWNER/REPO`; recent commit keys → Jira project;
an existing `emkeel.toml`); only **ask** for what's missing.

You also need a **Jira key** for the setup branch. Ask for one.
- **Trial run:** tell them any placeholder is fine — e.g. `SCRUM-9999` — because the check only
  reads the key's *pattern*, it does **not** verify the ticket exists, and you'll discard
  everything at the end anyway.
- **Real adoption:** use a real ticket (existing, or one they create, e.g. `SCRUM-123`).

→ Existing repo: Step 1A · New project: Step 1B.

## Step 1A — Existing repo
**Explain to the user first, in plain words:**
> "I'll make a **new branch** (I won't touch your `main`), so all of this becomes a normal Pull
> Request you can review and either accept or throw away. The branch is named with your ticket
> key so Emkeel's own check passes. Nothing is permanent until you merge."

Then:
- 🤖 `git checkout -b chore/<KEY>-adopt-emkeel`
- 🤖 `emkeel init . --github-repo … --jira-url … --jira-project … --dry-run` — show the plan and
  explain each file in one line (config, the CI check, the governance folder, agent guidance).
- 🤖 Run it for real (non-clobbering — it never overwrites your files).
- 🤖 **Stage ONLY the files Emkeel created** (plus the `.gitattributes`/`.gitignore` edits) —
  **never `git add -A`** (that would sweep in unrelated files). Commit and push the branch.
- 🤖 Do **not** make the `gates` check "required" yet — that way it can't block your existing CI.

## Step 1B — New project
Explain, then: 🤖 `git init`, `emkeel init . …`, commit, and create the GitHub repo (private).

## Step 2 — Connect (secrets)
> 🔒 **Security — you never handle secrets.** Never ask the user to paste a token/password into
> this chat, and never write a secret value into any file. The user types secrets **directly**
> into GitHub's encrypted **Secrets** page (or a gitignored `.env`). You only relay links + the
> secret **names**, and explain what each is for.

- **Trial run → SKIP this step.** Tell the user: *"I'm skipping the secrets for the trial — the
  check still runs fine without them; only the Jira auto-close stays inactive."*
- **Real adoption →** relay these one at a time (explain each):
  - 👤 1. Create a Jira API token — https://id.atlassian.net/manage-profile/security/api-tokens
  - 👤 2. Add repo secrets `JIRA_BASE_URL` / `JIRA_EMAIL` / `JIRA_TOKEN` —
    `https://github.com/OWNER/REPO/settings/secrets/actions/new` *(paste the token THERE, not here)*
  - 👤 3. Branch protection on `main` (require the `gates` check + a PR) —
    `https://github.com/OWNER/REPO/settings/branches`
  - 👤 4. (optional) GitHub for Jira app — https://github.com/marketplace/jira-software-github

## Step 3 — Verify, then finish
- 🤖 Open a small PR from the branch. Show the user the **`gates` check** result and explain it
  ("green = your change links a ticket and the rules pass").
- **Trial run →** once they've seen the green check, **clean up**: close the PR **without
  merging**, then `git checkout main` and `git branch -D chore/<KEY>-adopt-emkeel`. Confirm to
  the user that the repo is **exactly as before** — nothing was kept.
- **Real adoption →** 👤 approve + merge the PR. 🤖 Confirm the linked ticket moved to Done.

## Rules
- **Narrate before acting** — say what and why, in plain language; wait for the user's OK.
- Branch + PR — **never commit to `main`**. Stage **only** Emkeel's files (no `git add -A`).
- **Never put secrets in this chat or in a committed file.**
- One install method only. Committed artifacts in English; conversation in the user's language.
