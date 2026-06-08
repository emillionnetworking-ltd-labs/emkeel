# KEEL-46 — Interactive eject (ask + confirm by default)

## Context
`emkeel eject` was flag-driven: `--purge --yes` removed everything with no confirmation, and a
user could `--purge` (local) yet stay connected remotely (forgot `--remote`). Destructive actions
should confirm. `--yes` is the standard "don't prompt" opt-out, so the fix is a safe interactive
default.

## Plan
- `src/emkeel/uninstall.py` — make `eject` **interactive by default**: show what was found, ask per
  category (wiring / emkeel-governance/ / GitHub side), then ONE final "⚠ proceed?" before doing
  anything; print the teardown reminder (`pipx uninstall emkeel`) at the end. `--yes` stays as the
  non-interactive opt-out (scripts/CI); `--all` = wiring+governance+remote; `--dry-run` previews.
  A non-TTY without `--yes` refuses (won't guess). `tests/test_uninstall.py`. Bump 0.1.30.

## Acceptance Criteria
- `emkeel eject` (no flags, interactive) asks per category + a final confirmation; declining the
  first question or the final confirm changes nothing.
- Confirming removes the chosen parts (wiring always; governance/remote when confirmed).
- `--yes` applies without prompts; `--dry-run` only previews; non-TTY without `--yes` exits 1.
- The end prints the teardown order (un-govern repo → then `pipx uninstall emkeel`).

## Anti-regression
- Tests cover: dry-run preview, interactive wiring+governance, final-confirm cancel, decline-first,
  plus the existing apply_uninstall / remote_cleanup units.
