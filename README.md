# Emkeel

**Adopt-and-thin SDLC governance for AI-assisted teams.** Emkeel turns a repo into a
governed project: every change flows ticket → branch → PR → deterministic CI gates →
human-approved merge → the ticket closes itself. `"done"` is a **computed fact**, never a
self-attested flag — enforcement lives server-side (CI + branch protection), out of the
agent's reach.

## Install

Emkeel is a **zero-dependency** Python CLI (needs **Python 3.11+**). Recommended installer:
[`pipx`](https://pipx.pypa.io). Pick your platform:

| Platform | Install |
| --- | --- |
| **Windows** | `py -m pip install --user pipx` → `py -m pipx ensurepath` → `pipx install emkeel` |
| **macOS** | `brew install pipx` → `pipx install emkeel` |
| **Linux** (Debian/Ubuntu) | `sudo apt install pipx` → `pipx install emkeel` |
| **Locked-down server** (no sudo, no `python3-venv`) | `pip install --user --break-system-packages emkeel` |

The locked-down `pip --user` path is **safe**: emkeel has no runtime dependencies, so nothing
can conflict in your user site. (Plain `pip install emkeel` is blocked on PEP 668 Linux/macOS
— that's why the table uses pipx, or `--user --break-system-packages`.)

**Upgrade:** `pipx upgrade emkeel` · **Check version:** `emkeel version`

## Set up your repo

1. **Open your project** in your editor — an existing repo, or a new empty folder.
2. **Run the guided setup:**

   ```bash
   emkeel onboard
   ```

   Paste its output to your AI coding agent (Claude Code, Cursor, …) — it scaffolds and connects
   the repo **in your language**, handing you the exact links for the steps only you can do
   (create secrets, turn on branch protection). Or follow the printed steps yourself.

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
