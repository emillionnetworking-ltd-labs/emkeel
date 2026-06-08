# KEEL-52 — i18n for connect / eject / sync

## Context
`connect`, `eject` and `sync` were English-only, so a user who picked Spanish in `setup` still
saw English prompts/confirmations. Each command should run in the user's language.

## Plan
- `src/emkeel/i18n.py` — shared `t(catalog, key, lang)` + `ask_language()` + `is_yes()`.
- `connect.py`, `uninstall.py` (eject), `sync.py` — bilingual catalogs (es/en); render via `t`.
  `eject` asks language first (interactive); `connect`/`sync` take a `lang` param (inherited from
  `setup`) and ask when run standalone. `--lang es|en` flag on each. `setup` passes its language
  to `connect` (and `connect` to `sync`). `tests/` updated. Bump 0.1.36.

## Acceptance Criteria
- eject/connect/sync render their prompts + results in es or en.
- Launched from `setup`, connect/sync use the wizard's language (no re-asking).
- Run standalone, each asks language (or honours `--lang`).

## Anti-regression
- Tests pass `lang="en"` to the interactive command mains; remote_cleanup labels localized
  (assertions made language-robust).
