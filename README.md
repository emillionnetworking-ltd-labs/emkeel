# Emkeel

**SDLC governance for AI-assisted teams, built on GitHub + Jira.** Emkeel turns a repo into a
governed project: every change flows ticket → branch → PR → deterministic CI gates →
human-approved merge → the ticket closes itself. `"done"` is a **computed fact** (a check
passes), never a self-attested flag — enforcement lives server-side (GitHub Actions + branch
protection), out of the agent's reach.

> **Built for GitHub + Jira.** If your team isn't on both, Emkeel isn't for you (yet).

## Prerequisites (set these up first)

| Need | Where | Notes |
| --- | --- | --- |
| **GitHub account + a repo** | new repo → https://github.com/new | or use one you already have |
| **GitHub CLI `gh`**, authenticated | https://cli.github.com → then run `gh auth login` | also sets up your `git push`/`pull` auth (SSH or HTTPS) — no separate SSH setup needed |
| **Jira Cloud account** | https://www.atlassian.com/software/jira | your tickets live here |
| **Jira API token** | https://id.atlassian.net/manage-profile/security/api-tokens | you paste it into a hidden prompt; Emkeel verifies it before saving |
| **Python 3.11+** | https://www.python.org/downloads *(Windows: tick "Add python.exe to PATH"; or `winget install Python.Python.3.12`)* | Emkeel has zero other deps |

## 1. Install Emkeel (per platform)

**Only this step differs by OS.**

| Platform | Command |
| --- | --- |
| **Windows** | `py -m pip install --user pipx` → `py -m pipx ensurepath` → `py -m pipx install emkeel` |
| **macOS** | `brew install pipx` → `pipx install emkeel` |
| **Linux** (admin/sudo) | `sudo apt install pipx` → `pipx install emkeel` |
| **Linux/server, no sudo** | `pip install --user --break-system-packages emkeel` *(safe — zero deps)* |

Confirm: `emkeel version`.

> **Windows notes** (save yourself the headaches):
> - Use **`py -m pipx …`** (not bare `pipx`) — it works even before `pipx` lands on your PATH.
> - After installing Python or running `ensurepath`, **open a new terminal** — and in VS Code, **fully
>   restart the app** (its terminal caches the PATH from launch). Then `emkeel version`.
> - No Python yet? `py`/`python` "not recognized" means it isn't installed — do the prerequisite first.

## 2. Set up your repo

**First, open a terminal:**
- **VS Code / Cursor:** menu **Terminal → New Terminal** (or `` Ctrl+` ``).
- **Or your OS terminal:** Linux `Ctrl+Alt+T` · macOS *Terminal.app* · Windows *PowerShell*.

The wizard then guides you **in your language** (Spanish/English) and confirms before each step
(`c` cancels). Pick your path:

### A · You already have a repo
```bash
cd my-project
emkeel setup
```
1. Choose **language** (Español / English).
2. Choose **"Existing repo"**.
3. Confirm your **GitHub repo** + **Jira** (auto-detected — Enter to accept).
4. Enter a **Jira key** for the branch → it creates `chore/<KEY>-adopt-emkeel` + Emkeel's files + commit.
5. **"Connect now?" → yes:** branch protection (require the `gates` check + PRs) + **Jira secrets**
   (email + token **verified before saving**, hidden).
6. **"Finish the adopt?" → yes:** push → open the PR → **auto-merge when the gates pass** → sync your local.

✅ Your repo is governed (via a merged PR).

### B · New project (from scratch)
```bash
mkdir my-app && cd my-app
emkeel setup
```
1. Choose **language**.
2. Choose **"New project"**.
3. Type your **GitHub repo** (`owner/repo`) + **Jira** → it runs `git init` + Emkeel's files + commit.
4. **"Connect now?" → yes:** it **creates the GitHub repo and pushes it** (`gh repo create`) +
   branch protection + **Jira secrets** (verified).

✅ Your new repo is live on GitHub, governed.

> **Check what's set up / still pending anytime:** `emkeel doctor`.
> *Scripted instead?* `emkeel init` (non-interactive) · `emkeel connect` / `emkeel sync` standalone.

## 3. Remove Emkeel

**Order matters: un-govern the repo first, then uninstall the tool.** Open a terminal (see §2).

### Step 1 — Un-govern a repo (`emkeel eject`)
```bash
cd my-project
emkeel eject
```
1. Choose **language**.
2. Answer **3 yes/no questions**: remove the **wiring**? *(the basics)* · also **`emkeel-governance/`**? ·
   also the **GitHub side**? *(branch protection + secrets + push the removal)*.
3. Review the **summary** → **confirm**.
> *(Scripting/CI? `emkeel eject --help` shows the non-interactive flags.)*

### Step 2 — Uninstall the tool
```bash
pipx uninstall emkeel
```

> **Uninstalling the tool ≠ un-governing your repos.** If you only `pipx uninstall emkeel`, your
> repos' governance **keeps working** (their CI installs Emkeel from PyPI) — you just can't run the
> local `emkeel` commands to change it. **To remove everything: `emkeel eject` in each repo first,
> then `pipx uninstall emkeel`.**

## 4. All commands (by use)

**Set up / adopt**

| Command | What it does |
| --- | --- |
| `emkeel setup` | interactive wizard (recommended — does everything) |
| `emkeel connect` | just the GitHub side (branch protection + secrets), standalone |
| `emkeel init .` | scaffold non-interactively (for scripts/CI) |

**Check / maintain**

| Command | What it does |
| --- | --- |
| `emkeel doctor` | what's set up / what's pending (with fix links) |
| `emkeel sync` | after a merge: checkout default + pull + drop the merged branch |
| `emkeel review <KEY>` | per-criterion review template for a ticket |
| `emkeel version` | installed version (+ flags a newer one on PyPI) |

**Remove**

| Command | What it does |
| --- | --- |
| `emkeel eject` *(alias `emkeel uninstall`)* | un-govern the repo — interactive, asks what to remove (`--help` for CI flags) |
| `pipx uninstall emkeel` | remove the tool from your machine |

**Tool**

| Command | What it does |
| --- | --- |
| `pipx upgrade emkeel` | update the Emkeel tool |
| `emkeel update` | after upgrading, refresh an adopted repo's wiring to the new version |

## Keeping up to date

Three layers update independently — know which is which:

| Layer | Updates how |
| --- | --- |
| **The `emkeel` tool** (your CLI) | `pipx upgrade emkeel` |
| **A repo's CI gates** (the enforcement) | **automatic** — CI installs `emkeel~=0.MINOR.0` on every run, so the gate logic is always current. Nothing to do. |
| **A repo's generated files** (AGENTS.md, CLAUDE.md, workflow YAMLs) | `emkeel update` in the repo (then commit) — they were written at adoption and don't change on upgrade |

`emkeel doctor` tells you when a repo's files are older than your installed tool, so you'll know when to run `emkeel update`. **Updates are safe:** the CI pin auto-takes patches/minors; a breaking major is opt-in.

## What you get

- **Deterministic CI gates** (server-side, can't be skipped): every change links a ticket;
  features carry a spec with acceptance criteria; the full test suite runs on every PR.
- **Auto-close** — merging a PR moves the linked Jira ticket to Done.
- **AI review-assist** — a per-criterion verdict against the spec before you merge.
- **Clean separation** — governance artifacts live in one `emkeel-governance/` folder, never shipped.

See `docs/lifecycle.md` for the model.

---
Licensed under **Apache-2.0** — © 2026 EMillion Networking LTD (see `LICENSE` / `NOTICE`).
