# Emkeel

**SDLC governance for AI-assisted teams, built on GitHub + Jira.** Emkeel turns a repo into a
governed project: every change flows ticket → branch → PR → deterministic CI gates →
human-approved merge → the ticket closes itself. `"done"` is a **computed fact** (a check
passes), never a self-attested flag — enforcement lives server-side (GitHub Actions + branch
protection), out of the agent's reach.

> **Built for GitHub + Jira.** Emkeel uses GitHub (Actions CI, branch protection, the `gh` CLI)
> and Jira (tickets + transitions). If your team isn't on both, Emkeel isn't for you (yet).

## 1. Install Emkeel (per platform)

Zero-dependency Python CLI (needs **Python 3.11+**). **Only this step differs by OS** —
everything after is identical.

| Platform | Command |
| --- | --- |
| **Windows** | `py -m pip install --user pipx` → `py -m pipx ensurepath` → `pipx install emkeel` |
| **macOS** | `brew install pipx` → `pipx install emkeel` |
| **Linux** (with admin/sudo) | `sudo apt install pipx` → `pipx install emkeel` |
| **Linux/server, no sudo** | `pip install --user --break-system-packages emkeel` *(safe — zero deps)* |

Confirm with `emkeel version`. *(No pipx and can't install it? the last row works anywhere.)*

## 2. Set up your repo — step by step

The wizard is **the same on every OS** and **deterministic (no AI)**.

1. **Open a terminal** in your project folder (an existing repo), or in a **new empty folder**
   (a new project).
2. **Run the wizard:**
   ```bash
   emkeel setup        # one-shot, without installing first:  pipx run emkeel setup
   ```
3. **Answer its questions** (in your language): existing repo or new project, then confirm your
   **GitHub repo** and **Jira** (project + URL). Press **`c`** to cancel any menu.
4. It **creates the branch + files + commit** and prints your remaining steps.
5. **Do the connect steps it printed** — one-time, only you can:
   - **Create a Jira API token** → https://id.atlassian.net/manage-profile/security/api-tokens
   - **Add it as a GitHub secret** (`JIRA_TOKEN`, `JIRA_BASE_URL`, `JIRA_EMAIL`) in the repo's
     **Settings → Secrets** *(🔒 never paste a token into a chat or commit it)*
   - **Turn on branch protection** (require the `gates` check + a PR) in **Settings → Branches**
6. **Check anytime:** `emkeel doctor` tells you what's still pending. **Undo:** `emkeel eject`.

That's it — your repo is governed by Emkeel.

> Skipped a connect step? Emkeel tells you: `emkeel doctor` lists the gaps, and the CI itself
> warns (e.g. a merge without the secrets logs *"auto-close is OFF — set secrets"*).

## 3. Managing Emkeel

| You want to… | Command |
| --- | --- |
| **See what's set up / pending** | `emkeel doctor` |
| **Check version / updates** | `emkeel version` |
| **Upgrade the tool** | `pipx upgrade emkeel` |
| **Un-govern a repo** | `emkeel eject` *(dry-run; add `--yes` to apply; keeps `emkeel-governance/` unless `--purge`)* |
| **Re-govern a repo** | `emkeel setup` again |
| **Uninstall the tool** | `pipx uninstall emkeel` |

> **Use one install method** (don't mix pipx with `pip --user`). **Updates are safe:** your
> repo's CI pins `emkeel~=0.MINOR.0` — auto patches/minors; a breaking major is opt-in.

## What you get

- **Deterministic CI gates** (server-side, can't be skipped): every change links a ticket;
  features carry a spec with acceptance criteria; the full test suite runs on every PR.
- **Auto-close** — merging a PR transitions the linked Jira ticket to Done.
- **AI review-assist** — a per-criterion verdict against the spec before you merge.
- **Clean separation** — governance artifacts live in one `emkeel-governance/` folder, never shipped.

*AI-assisted onboarding (`emkeel onboard`) exists; a richer AI experience is in progress.*
See `docs/lifecycle.md` for the model.

---
Licensed under **Apache-2.0** — © 2026 EMillion Networking LTD (see `LICENSE` / `NOTICE`).
