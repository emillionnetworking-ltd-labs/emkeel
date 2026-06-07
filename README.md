# Emkeel

**Adopt-and-thin SDLC governance for AI-assisted teams.** Emkeel turns a repo into a
governed project: every change flows ticket → branch → PR → deterministic CI gates →
human-approved merge → the ticket closes itself. `"done"` is a **computed fact**, never a
self-attested flag — enforcement lives server-side (CI + branch protection), out of the
agent's reach.

## Getting started (AI-assisted — recommended)

**You'll need:** Python 3.11+, [`pipx`](https://pipx.pypa.io) (`sudo apt install pipx` on
Debian/Ubuntu), `git`, a GitHub account, a Jira account + a project, and an IDE with an AI
coding agent — e.g. **VS Code with Claude Code**, or Cursor.

1. **Open your project in your AI IDE** — either an **existing repo** you already have, or a
   **new empty folder** for a project from scratch.
2. **Tell your AI agent, verbatim:**

   > Install and set up Emkeel in this repo: install it with `pipx install emkeel` (or `pip`
   > inside a venv), then run `emkeel onboard`, and follow what it prints. Ask me for my
   > GitHub repo, Jira URL, and Jira project key.

3. The agent installs Emkeel, runs the guided onboarding, and walks you through the rest
   **in your language**, handing you the **exact links** for the steps only you can do
   (create secrets, turn on branch protection).

> Prefer to run it yourself? `pipx install emkeel`, then `emkeel onboard`, and follow it.
> (No pipx? Use a venv: `python3 -m venv .venv && . .venv/bin/activate && pip install emkeel`.
> Plain `pip install emkeel` fails on modern systems — externally-managed, PEP 668.)

## Manual setup (no AI)

Prefer to do it by hand? Run `emkeel init` and follow the printed checklist:

```bash
# existing repo
emkeel init . --github-repo OWNER/REPO --jira-url https://you.atlassian.net --jira-project KEY

# new project
mkdir my-project && cd my-project && git init
emkeel init . --github-repo OWNER/REPO --jira-url https://you.atlassian.net --jira-project KEY
```

`emkeel init` is non-clobbering (add `--dry-run` to preview) and prints the exact links to
finish setup. Full guide: `docs/install.md`.

## What you get

- **Deterministic CI gates** (server-side, can't be skipped): every change links a ticket;
  features carry a spec with acceptance criteria; the full test suite runs on every PR.
- **AI review-assist** — a per-criterion verdict against the spec before you merge.
- **Auto-close** — merging transitions the linked Jira ticket to Done.
- **Clean separation** — governance artifacts live in one `emkeel-governance/` folder, never shipped.

See `docs/lifecycle.md` for the model.

---
Licensed under **Apache-2.0** — © 2026 EMillion Networking LTD (see `LICENSE` / `NOTICE`).
