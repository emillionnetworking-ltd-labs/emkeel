# KEEL-23 — emkeel version + update awareness

## Context
Users need to know which version they run and when a newer one ships. The repo is private,
so PyPI is the public source of truth. `emkeel --version` didn't even exist. Updates must be
safe: the generated CI pins `emkeel~=0.MINOR.0`, so patches/minors flow automatically and a
breaking major is opt-in.

## Plan
- `src/emkeel/version.py` — `emkeel version`: print installed version; best-effort PyPI check
  (3s timeout, silent on failure, skippable via `EMKEEL_NO_UPDATE_CHECK=1`) that prints an
  "update available — pipx upgrade emkeel" line when newer.
- `src/emkeel/cli.py` — dispatch `version` / `--version` / `-V`.
- `tests/test_version.py`; document upgrade in `docs/install.md`.

## Acceptance Criteria
- `emkeel version` (and `emkeel --version`) prints the installed version.
- When PyPI has a newer version, it prints an "update available … pipx upgrade emkeel" hint.
- The check is silent on network failure and skipped when `EMKEEL_NO_UPDATE_CHECK` is set.
- Docs explain upgrading (`pipx upgrade emkeel`) and that the CI pin auto-takes patches/minors.

## Anti-regression
- Tests cover: update-line logic (newer/current/older/unknown), injected/failed PyPI fetch,
  and that `version` prints the installed version.
