# Emkeel

**Adopt-and-thin SDLC governance for AI-assisted teams.** Emkeel turns a repo into a
governed project: every change flows ticket → branch → PR → deterministic CI gates →
human-approved merge → the ticket closes itself. `"done"` is a **computed fact**, never a
self-attested flag — enforcement lives server-side (CI + branch protection), out of the
agent's reach.

## Install (quick reference)

Emkeel is a **zero-dependency** Python CLI (needs **Python 3.11+**). New to the command line?
Jump to the **step-by-step guide** below.

| Platform | Install |
| --- | --- |
| **Windows** | `py -m pip install --user pipx` → `py -m pipx ensurepath` → `pipx install emkeel` |
| **macOS** | `brew install pipx` → `pipx install emkeel` |
| **Linux** (with admin/sudo) | `sudo apt install pipx` → `pipx install emkeel` |
| **Linux/server without sudo** | `pip install --user --break-system-packages emkeel` *(safe — zero deps)* |

**Upgrade:** `pipx upgrade emkeel` · **Check version:** `emkeel version`
*(Switching from `pip` to pipx? Run `pip uninstall emkeel` first to avoid two copies.)*

## Getting started — step by step (Linux)

Two ways to set up: **AI-assisted (recommended)** or **manual**. Both start by installing Emkeel once.

### First: install Emkeel (one time)

1. **Open a terminal** — press **Ctrl + Alt + T** (or search "Terminal" in your apps).
2. **Check Python:** type `python3 --version`. You need **3.11+**.
3. **Install** (copy-paste the whole line):
   ```bash
   sudo apt install -y pipx && pipx ensurepath && pipx install emkeel
   ```
   `sudo` asks for **your login password** (the one you use to sign in). **Nothing shows on
   screen while you type it — that's normal.** Then **close the terminal and open a new one**.
   > **No sudo / "not in the sudoers file"?** You're not an admin. Use this (no admin, safe —
   > Emkeel has no dependencies): `pip install --user --break-system-packages emkeel`
4. **Confirm:** type `emkeel version` → should say `emkeel 0.1.x`.

### ⭐ Option A — AI-assisted (recommended)

1. **Open your project in your AI editor.** Open **VS Code** (or Cursor) and open your project
   folder (*File → Open Folder*). New project? Make an empty folder and open that.
2. **Open the AI chat panel** — in VS Code with Claude Code, click the Claude icon in the
   sidebar. (Cursor: open the chat with Ctrl/Cmd+L.)
3. **Type this in the chat:**
   > Set up Emkeel in this repo: run `emkeel onboard` and follow it.

   The assistant **explains each step in plain language as it goes**, and asks whether this is
   a **trial** (it cleans everything up afterwards) or a **real adoption**.
4. It will also **ask you three things** — answer with your details:
   - your **GitHub repo** — like `acme/web`
   - your **Jira address** — like `https://acme.atlassian.net`
   - your **Jira project key** — like `SCRUM`
5. The assistant scaffolds everything (on a branch + PR) and gives you a few **links** to finish.
   🔒 **Security — important:** create your Jira token and paste it **into GitHub's secret page**
   (the link the assistant gives you) or into a local `.env` file — **NEVER paste a token or
   password into the chat.** The assistant never needs to see your secrets.
6. Merge the small PR the assistant opens. **Done — your repo is governed by Emkeel.**

### Option B — Manual (no AI)

Prefer to do it yourself? On a new branch, run (with your details):

```bash
git checkout -b chore/SCRUM-1-adopt-emkeel
emkeel init . --github-repo OWNER/REPO --jira-url https://you.atlassian.net --jira-project KEY
```

It creates the files and prints the same connect links — follow them. Same rule: secrets go in
GitHub's secret page or `.env`, **never shared in plain text**.

## Managing Emkeel

There are **three separate things**, so "remove" means different things — pick the one you want:

| You want to… | Command | What it touches |
| --- | --- | --- |
| **Upgrade the tool** | `pipx upgrade emkeel` | the `emkeel` program on your machine |
| **Check the version** | `emkeel version` | (also flags a newer one on PyPI) |
| **Un-govern a repo** (remove Emkeel's files) | `emkeel eject` *(alias: `emkeel uninstall`)* | the repo's wiring: workflows, `emkeel.toml`, `.env.example`, `AGENTS.md`, `CLAUDE.md`. **Keeps** `emkeel-governance/` (your history) — add `--purge` to delete that too. |
| **Uninstall the tool** | `pipx uninstall emkeel` | removes the `emkeel` program from your machine |

> **`emkeel eject` does NOT remove the tool** — it reverses `emkeel init` inside one repo. It's a
> safe **dry-run** by default; add `--yes` to apply. It never strips lines you already had in
> `.gitignore`/`.gitattributes`. (And `emkeel onboard` installs nothing — it only **prints** the guide.)

**To remove Emkeel completely:**

```bash
emkeel eject --purge --yes   # in the repo: wiring + governance folder
pipx uninstall emkeel        # the tool, from your machine
```

> **Use one install method** — don't mix pipx with `pip --user`/venv (that creates conflicting
> copies). **Updates are safe:** your repo's CI pins `emkeel~=0.MINOR.0`, so it auto-takes
> patches and minors; a breaking major (e.g. `0.2.0`) is opt-in (you bump the pin).

## What you get

- **Deterministic CI gates** (server-side, can't be skipped): every change links a ticket;
  features carry a spec with acceptance criteria; the full test suite runs on every PR.
- **AI review-assist** — a per-criterion verdict against the spec before you merge.
- **Auto-close** — merging transitions the linked Jira ticket to Done.
- **Clean separation** — governance artifacts live in one `emkeel-governance/` folder, never shipped.

See `docs/lifecycle.md` for the model.

---
Licensed under **Apache-2.0** — © 2026 EMillion Networking LTD (see `LICENSE` / `NOTICE`).
