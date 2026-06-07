# Emkeel

**Adopt-and-thin SDLC governance for AI-assisted teams.** Emkeel turns a repo into a
governed project: every change flows ticket → branch → PR → deterministic CI gates →
human-approved merge → the ticket closes itself. `"done"` is a **computed fact**, never a
self-attested flag — enforcement lives server-side (CI + branch protection), out of the
agent's reach.

## Install

```bash
pip install emkeel
```

## Quickstart

**Add to an existing repo:**

```bash
cd your-repo
emkeel init . --github-repo OWNER/REPO --jira-url https://you.atlassian.net --jira-project KEY
```

**Or start a new project from scratch:**

```bash
mkdir my-project && cd my-project && git init
emkeel init . --github-repo OWNER/REPO --jira-url https://you.atlassian.net --jira-project KEY
```

`emkeel init` is **non-clobbering** (it never overwrites your files; add `--dry-run` to
preview) and prints a **guided checklist with the exact links** to finish setup (secrets,
branch protection).

## Two ways to set up

- **Manual** — run `emkeel init` and follow the printed checklist. Full guide: `docs/install.md`.
- **AI-assisted** — run `emkeel onboard` and paste its output to your coding agent
  (Claude Code, Cursor, …). It asks you for your repo/Jira details and sets Emkeel up
  **conversationally, in your language**, surfacing the links in real time.

## What you get

- **Deterministic CI gates** (server-side, can't be skipped): every change links a ticket;
  features carry a spec with acceptance criteria; the full test suite runs on every PR.
- **AI review-assist** — a per-criterion verdict against the spec before you merge.
- **Auto-close** — merging transitions the linked Jira ticket to Done.
- **Clean separation** — all governance artifacts live in one `emkeel-governance/` folder,
  never shipped in the package.

See `docs/lifecycle.md` for the model.

---
Licensed under **Apache-2.0** — © 2026 EMillion Networking LTD (see `LICENSE` / `NOTICE`).
