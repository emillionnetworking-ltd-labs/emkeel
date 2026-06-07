# Emkeel

**Adopt-and-thin SDLC governance for AI-assisted teams.** Emkeel turns a repo into a
governed project: every change flows ticket → branch → PR → deterministic CI gates →
human-approved merge → the ticket closes itself. `"done"` is a **computed fact**, never a
self-attested flag — enforcement lives server-side (CI + branch protection), out of the
agent's reach.

## Install (quick reference)

Emkeel is a **zero-dependency** Python CLI (needs **Python 3.11+**). New to the command line?
Use the **step-by-step guide below** instead of this table.

| Platform | Install |
| --- | --- |
| **Windows** | `py -m pip install --user pipx` → `py -m pipx ensurepath` → `pipx install emkeel` |
| **macOS** | `brew install pipx` → `pipx install emkeel` |
| **Linux** (with admin/sudo) | `sudo apt install pipx` → `pipx install emkeel` |
| **Linux/server without sudo** | `pip install --user --break-system-packages emkeel` *(safe — zero deps)* |

**Upgrade:** `pipx upgrade emkeel` · **Check version:** `emkeel version`

## Step-by-step for beginners (Linux)

Never used a terminal? Do exactly this, in order.

**1. Open a terminal.** Press **Ctrl + Alt + T** (or open your apps and search **"Terminal"**).
A window with a text prompt appears — you type a command, then press **Enter**.

**2. Check your Python version.** Type and press Enter:

```bash
python3 --version
```

You need **3.11 or higher**. If it's lower or says "command not found", install it with
`sudo apt install python3` (see the password note in step 3).

**3. Install Emkeel.** Copy-paste this whole line and press Enter:

```bash
sudo apt install -y pipx && pipx ensurepath && pipx install emkeel
```

- `sudo` means "do this as administrator" — it asks for **your login password** (the one you
  use to sign into the computer). **While you type it, nothing appears on screen — that's
  normal.** Type it and press Enter.
- When it finishes, **close the terminal and open a new one** so the `emkeel` command is found.

> **Don't have sudo / it says "not in the sudoers file"?** Then you're not an administrator on
> this machine. Use this instead — it needs **no admin** and is safe (Emkeel has no
> dependencies, so nothing can conflict):
>
> ```bash
> pip install --user --break-system-packages emkeel
> ```
>
> Then close and reopen the terminal. *(On a shared/company server you can also ask whoever
> manages it to run `sudo apt install pipx` once — then the normal step 3 works.)*

**4. Check it worked.** Type:

```bash
emkeel version
```

You should see `emkeel 0.1.x`. If it says "command not found", close and reopen the terminal
and try again.

**5. Open your project** in your editor (e.g. VS Code) — a project you already have, or a new
empty folder.

**6. Get your setup instructions.** Back in the terminal, type:

```bash
emkeel onboard
```

Then **select and copy everything it prints.**

**7. Hand it to your AI assistant.** Open your AI coding agent (e.g. Claude Code inside VS
Code), **paste** what you copied into its chat, and press Enter. It will ask you a few things
(your GitHub repo, your Jira address and project key) and set everything up for you —
including clickable links for the couple of steps only you can do (create secrets, turn on
branch protection).

*Done.* Your repo is now governed by Emkeel.

## Set up your repo (already installed)

```bash
emkeel onboard   # prints the AI playbook — paste it to your agent
```

**Manual (no AI):**

```bash
emkeel init . --github-repo OWNER/REPO --jira-url https://you.atlassian.net --jira-project KEY
```

Non-clobbering (add `--dry-run` to preview); prints the exact connect links. Full guide: `docs/install.md`.

## Managing Emkeel

| Action | Command |
| --- | --- |
| **Upgrade** | `pipx upgrade emkeel` |
| **Check version / updates** | `emkeel version` |
| **Remove from a repo** | `emkeel uninstall` (preview; add `--yes` to apply — keeps `emkeel-governance/`) |
| **Remove the tool** | `pipx uninstall emkeel` |

> **Use one install method** — don't mix pipx with `pip --user`/venv; that creates shadowing,
> conflicting installs. **Updates are safe:** your repo's CI pins `emkeel~=0.MINOR.0`, so it
> auto-takes patches and minors; a breaking major (e.g. `0.2.0`) is opt-in (you bump the pin).

## What you get

- **Deterministic CI gates** (server-side, can't be skipped): every change links a ticket;
  features carry a spec with acceptance criteria; the full test suite runs on every PR.
- **AI review-assist** — a per-criterion verdict against the spec before you merge.
- **Auto-close** — merging transitions the linked Jira ticket to Done.
- **Clean separation** — governance artifacts live in one `emkeel-governance/` folder, never shipped.

See `docs/lifecycle.md` for the model.

---
Licensed under **Apache-2.0** — © 2026 EMillion Networking LTD (see `LICENSE` / `NOTICE`).
