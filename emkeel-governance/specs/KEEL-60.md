# KEEL-60 — doctor flags stale wiring + README "Keeping up to date"

## Context
Nothing told users they must run `emkeel update` after `pipx upgrade` to refresh a repo's static
files. Make it discoverable (doctor) + documented (README). Auto-running update is intentionally
not silent (it modifies files).

## Plan
- `src/emkeel/init.py` — stamp `emkeel.toml` `[emkeel] generated_with = "<version>"`.
- `src/emkeel/doctor.py` — read the stamp + installed version; if the wiring is older (or unstamped),
  print "⚠ wiring older than your tool → run: emkeel update". `_older()` numeric compare.
- `README.md` — "Keeping up to date" section (tool via pipx · gates auto via CI pin · static files via
  emkeel update). `tests/`. Bump 0.1.46.

## Acceptance Criteria
- emkeel.toml carries `generated_with`; doctor nudges `emkeel update` when wiring < installed (or unstamped) and stays quiet when current.
- README explains the three update layers.

## Anti-regression
- Tests: stale wiring → nudge; current wiring → no nudge; _older(); toml stamped with generated_with.
