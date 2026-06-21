# KEEL-94 — Auto-guide the upgrade → update → connect flow

Strategy: none (wizard/UX tooling — not a product feature)

## Context
`doctor` already detects the pending work (wiring drift → `emkeel update`; missing scoped `.env` →
`emkeel connect`), but only if you run it. After `pipx upgrade emkeel` nothing tells the user to run
`emkeel update`, and `connect` re-asks blindly without showing what's already configured. This makes the
flow self-guiding, reusing doctor's signals, bilingual es/en.

## Plan (3 pieces, extending the existing code + i18n)
1. **Proactive nudge** (`cli.py` → `doctor.wiring_nudge`): on ANY non-exempt emkeel command, a cheap, LOCAL
   (no network), FAIL-SAFE one-line stderr hint — `generated_with < __version__` (cheap stamp) or
   `wiring_drift` → "run: emkeel update"; missing scoped `.env` → "run: emkeel connect". Honors
   `EMKEEL_NO_UPDATE_CHECK`; silent for `doctor`/`update`/`connect`/`guard`/`version` (no double-nudge; guard
   is hot). Never blocks/raises.
2. **`emkeel update` handoff**: on success, if the scoped credential is still pending → print
   "→ next: run `emkeel connect` … GH_TOKEN" — the user learns the command AND the variable.
3. **State-aware `emkeel connect`**: each step shows current state and only asks what's missing/changes —
   branch protection ("already on ✓ — change? [y/N]"), Jira secrets ("already set ✓ — reconfigure?"),
   scoped `.env` ("missing ✗ — configure" / "already configured ✓ — rewrite?"). Reuses `repo_exists`,
   new `protection_exists`/`secrets_exist`/`env_scoped_present`.

## Acceptance Criteria
1. The nudge appears (stderr) when wiring is behind and/or the scoped `.env` is missing; is silent when up
   to date; is skipped for the exempt commands; honors `EMKEEL_NO_UPDATE_CHECK`; never breaks the command.
2. `emkeel update` prints a handoff naming `emkeel connect` + the new variable (GH_TOKEN) when pending;
   nothing when the credential is present.
3. `emkeel connect` shows each step's state and, when already configured, only offers to change (declining
   re-does nothing); existing connect behavior preserved.
4. Bilingual es/en; cheap + fail-safe (no network in the nudge). All prior tests pass; bump 0.1.80.

## Notes
No ADR (UX refinement, no new architectural decision).
