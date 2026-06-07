# KEEL-22 — emkeel uninstall (reverse init)

## Context
Users need a clean, trustworthy way to remove Emkeel from a repo — the symmetric counterpart
of `emkeel init`. Removing the package (pip/pipx) doesn't touch the files init wrote. And the
governance trail (`emkeel-governance/`) is the user's data, so it must NOT be deleted casually.

## Plan
- `src/emkeel/uninstall.py` — `plan_uninstall` / `apply_uninstall` + a CLI: remove the wiring
  files (workflows, emkeel.toml, .env.example, AGENTS.md, CLAUDE.md), strip the appended
  `.gitattributes`/`.gitignore` lines, keep `emkeel-governance/` unless `--purge`.
- `src/emkeel/cli.py` — dispatch `emkeel uninstall`.
- `tests/test_uninstall.py`.

## Acceptance Criteria
- `emkeel uninstall` removes the wiring and strips the appended lines, but **keeps**
  `emkeel-governance/` by default.
- `--purge` also deletes `emkeel-governance/`.
- Default run is a **dry-run** (prints the plan, changes nothing); `--yes` applies it.
- `emkeel uninstall` dispatches from the `emkeel` CLI.

## Anti-regression
- Tests cover: wiring removed + governance kept; --purge deletes governance; dry-run is a no-op.
