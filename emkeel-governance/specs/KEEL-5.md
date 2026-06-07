# KEEL-5 — `emkeel init` installer

## Context
Makes Emkeel usable beyond itself: scaffolds a target repo to be governed by Emkeel
(governance folder, CI gates, connection config) without touching what already exists.
This is the step toward governing other repos (eventually em-ecosystem).

## Plan
- `src/emkeel/init.py` — `plan()`/`apply()` + templates + CLI (`python -m emkeel.init`).
- `tests/test_init.py` — plan, non-clobber, --force, append idempotency, dry-run, main().
- `docs/install.md` — how to run it + the connection checklist.

## Acceptance Criteria
- `python -m emkeel.init <target>` creates `emkeel-governance/{specs,adr,records}`,
  `.github/workflows/emkeel-ci.yml`, `emkeel.toml`, `.env.example`, and appends the
  `export-ignore` / `.env` lines.
- Non-clobber: an existing target file is reported `skip-exists` and left untouched, unless `--force`.
- `--dry-run` writes nothing and reports the planned actions.
- No secret is ever written to a committed file (only `.env.example` template; no `.env`).
- The command prints a connection checklist for Jira + GitHub.

## Anti-regression
- Tests cover: full plan on an empty target, non-clobber with an existing file, `--force`,
  append idempotency (line present vs absent), dry-run writes nothing, apply idempotency,
  and `main()` smoke.
