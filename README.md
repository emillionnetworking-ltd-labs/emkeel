# Emkeel

**Adopt-and-thin SDLC governance for AI-assisted teams.** Emkeel turns a repo into a
governed project: every change flows ticket → branch → PR → deterministic CI gates →
human-approved merge → the ticket closes itself. `"done"` is a **computed fact**, never a
self-attested flag — enforcement lives server-side (CI + branch protection), out of the
agent's reach.

## Getting started (AI-assisted — recommended)

**You'll need:** Python 3.11+ (with `pip`), `git`, a GitHub account, a Jira account + a
project, and an IDE with an AI coding agent — e.g. **VS Code with Claude Code**, or Cursor.

1. **Open your project in your AI IDE.** Open the folder you want to govern — either:
   - an **existing repo** you already have (Emkeel adds governance to it), or
   - a **new empty folder** (Emkeel helps you start a governed project from scratch).
2. **Install Emkeel:**
   ```bash
   pip install emkeel
   ```
3. **Start the guided setup, then paste it to your agent:**
   ```bash
   emkeel onboard
   ```
   Copy the printed output into your AI agent's chat. It asks you a couple of questions
   (existing repo or new? your GitHub repo, Jira URL, project key) and then sets everything
   up **in your language**, handing you the **exact links** for the steps only you can do
   (create secrets, turn on branch protection).

That's it — the agent drives the rest, one step at a time.

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
