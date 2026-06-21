# KEEL-93 — Automate credential isolation in the wizard (scoped GitHub PAT + per-repo .env)

Strategy: none (governance/security tooling — the wizard, not a product feature)

## Context
ADR-0006's isolation guard bounds *what* a token may do, but the **local** GitHub credential was still
manual → a new user got isolation they couldn't actually use. This automates it in the wizard, exactly as
emkeel already automates the Jira token (bilingual es/en, hidden `getpass` paste — never via chat, guided
with the right URL, dry-run preview). Evolves the secrets model (ADR-0007).

## Plan
1. **New wizard step** (`connect.py`, section 3b): guide the user to a **fine-grained PAT scoped to THIS
   repo** (the fine-grained-tokens URL, *Only select repositories → <repo>*, min perms Contents RW /
   Pull requests RW / Metadata R), then a **hidden paste** (`getpass`). Bilingual strings + a dry-run line.
2. **Write `.env` per-repo** — `write_env()`: upserts `GH_TOKEN` (+ Jira creds) into `.env`, **chmod 600**,
   gitignored, idempotent, never clobbering other vars.
3. **Per-repo loading**: a committed **`.envrc`** (plain bash `set -a; . ./.env; set +a`) — direnv
   auto-loads it per directory (`direnv allow`), or `source .envrc`. Non-secret scaffold (`.envrc`,
   extended `.env.example`) ships via `_files` → init/update deliver it.
4. **`emkeel update`** delivers the scaffold; **`emkeel doctor`** detects a missing scoped `.env`
   (`GH_TOKEN`) and prints a bilingual "→ run: emkeel connect".
5. **ADR-0007**: "scoped secrets in a gitignored, 600 `.env`" replaces "never write secrets" for the local
   per-window credential; CI GitHub Secrets unchanged. Bump 0.1.79.

## Acceptance Criteria
1. The wizard prompts for the scoped PAT via a **hidden** paste and never echoes it.
2. `write_env` writes `.env` with `chmod 600`, idempotent, preserving the user's other vars.
3. The non-secret scaffold (`.envrc`, extended `.env.example`) ships via `_files`; `init` never writes a
   secret `.env`; `.env` stays gitignored.
4. `emkeel doctor` flags a missing scoped `.env` (bilingual) and is silent when present.
5. Existing wizard/connect behavior is preserved (all prior tests pass, sequences updated for the new step).

## Reported mechanism
Per-repo loading = a committed **`.envrc`** auto-loaded by **direnv** (directory-scoped), with a manual
`source .envrc` fallback — zero Python dependency; the wizard guides activation like it guides the Jira token.
