# 7. Scoped local credentials in a gitignored `.env` (chmod 600), written by the wizard

- Status: accepted
- Date: 2026-06-21
- Deciders: operator (EMillion Networking)
- Ticket: KEEL-93

## Context

ADR-0006 made the per-repo isolation guard real, and emkeel's wizard already configures Jira (a hidden
paste → GitHub Secrets for CI). But the **local** credential — the GitHub token the agent's `gh`/`git`
use inside a window — was still configured by hand. A new user got a guard that bounds *what* a token may
do, but no automated way to obtain a **repo-scoped token** and load it per-window. The result: the agent
either had a broad token (defeating isolation) or none (the product is unusable). `init.py` also stated
"secrets are NEVER written", which left the scoped credential as a manual, undocumented step.

The isolation model needs each window to carry a credential that **physically can't reach another repo**:
a GitHub **fine-grained PAT scoped to one repo**, present **only** in that window.

## Decision

The wizard (`emkeel connect`) now configures the **scoped local credential**, in the same proven style as
the Jira step (bilingual es/en, **hidden `getpass` paste — never via chat**, guided with the exact URL,
dry-run preview):

1. It guides the user to create a **fine-grained PAT scoped to THIS repo** (the
   `Settings → Developer settings → Fine-grained tokens` URL, *Only select repositories → <repo>*,
   minimum permissions **Contents RW · Pull requests RW · Metadata R**), then takes a **hidden paste**.
2. It writes **`.env`** — **gitignored, `chmod 600`** — with `GH_TOKEN` (+ the Jira creds already
   collected), **upserting** keys so it never clobbers the user's other vars; idempotent.
3. **Per-repo loading** is a committed **`.envrc`** (plain bash: `if [ -f .env ]; then set -a; . ./.env;
   set +a; fi`) — auto-loaded per-directory by **direnv** (`direnv allow`), and also `source`-able by
   hand. So each window loads **only its own** `.env`. The non-secret scaffold (`.envrc`, extended
   `.env.example`) ships via `_files`, so `init`/`update` deliver it; `.env` stays gitignored.
4. `emkeel doctor` detects a missing scoped credential (`.env` without `GH_TOKEN`) and prints a bilingual
   "→ run: emkeel connect". `emkeel update` delivers the wiring; the secret is pasted by `connect`.

**This evolves the secrets model**: "emkeel never writes secrets" becomes "**`init` never writes secrets;
`connect` writes the SCOPED local credential to a gitignored, `chmod 600` `.env`**". The credential is
already bounded (a one-repo fine-grained PAT), and a gitignored `0600` `.env` + direnv is the standard,
auditable pattern — strictly safer than a long-lived broad token in the shell rc. **CI GitHub Secrets are
unchanged** (Jira creds still set via `gh secret set`).

## Consequences

- **Isolation is usable out of the box**: the wizard produces a repo-scoped token loaded only in its
  window, complementing ADR-0006's guard (which bounds cross-repo *actions*).
- **Chosen loading mechanism — direnv `.envrc`** (with a manual `source .envrc` fallback): directory-scoped
  by construction, zero *Python* dependency (the loader is bash; direnv is an optional shell tool the
  wizard guides the user to activate, exactly as it guides the Jira token). Reported as the mechanism.
- **No clobber**: `.env` is upserted (other vars preserved); `.envrc`/`.env.example` ship via the existing
  non-clobbering `_files` path; `.env` stays gitignored (the `.gitignore` append manifest).
- **Secrets boundary stays clear**: only `connect` writes `.env`, only from a hidden paste, never echoed;
  `init`/`update` deliver non-secret scaffold only. emkeel governs itself (ships its own `.envrc` +
  `.env.example`).
- **Trade-off**: a secret now lives on disk (gitignored, `0600`) instead of "nowhere local". Accepted: the
  token is repo-scoped and the file is owner-only + gitignored — the standard local-dev posture, and the
  only way to make per-window isolation real without a broad token.
