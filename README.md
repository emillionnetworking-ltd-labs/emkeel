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

1. **Open your project in your AI IDE** — an existing repo, or a new empty folder.
2. **Tell your AI agent, verbatim:**

   > Install and set up Emkeel in this repo: install it with `pipx install emkeel`, then run
   > `emkeel onboard`, and follow what it prints. Ask me for my GitHub repo, Jira URL, and
   > Jira project key.

3. The agent installs Emkeel, runs the guided onboarding, and walks you through the rest
   **in your language**, handing you the exact links for the steps only you can do
   (create secrets, turn on branch protection).

## Managing Emkeel

| Action | Command |
| --- | --- |
| **Install** | `pipx install emkeel` |
| **Check version / updates** | `emkeel version` |
| **Upgrade** | `pipx upgrade emkeel` |
| **Set up a repo** | `emkeel onboard` (AI-guided) · or `emkeel init` (manual, below) |
| **Remove from a repo** | `emkeel uninstall` (preview; add `--yes` to apply — keeps `emkeel-governance/`) |
| **Remove the tool** | `pipx uninstall emkeel` |

> **No `pipx`?** Use a venv: `python3 -m venv .venv && . .venv/bin/activate && pip install emkeel`.
> (Plain `pip install emkeel` fails on modern systems — externally-managed, PEP 668.)
>
> **Updates are safe:** your repo's CI pins `emkeel~=0.MINOR.0`, so it auto-takes patches and
> minors; a breaking major (e.g. `0.2.0`) is opt-in — you bump the pin yourself.

## Manual setup (no AI)

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
