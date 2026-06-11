# KEEL-69 — _clean_local cleans emkeel.toml when only the version stamp differs

## Context
Verified in em-ecosystem: `emkeel update` shipped only emkeel files (PR #375, merged) and cleaned
AGENTS.md/workflow/strategy, but **emkeel.toml stayed pending** — its `generated_with` stamp differed
(local 0.1.52 vs template 0.1.54), so _clean_local's hand-edit guard skipped it.

## Plan
- `src/emkeel/ship.py` — `_clean_local`: for emkeel.toml, compare the local file to the COMMITTED
  version IGNORING the `generated_with` line (`_strip_stamp`). Same → only the stamp changed → clean;
  values changed (e.g. project_key) → keep. `tests/test_ship.py`. Bump 0.1.55.

## Acceptance Criteria
- A leftover emkeel.toml that differs only by the version stamp gets cleaned (reverted).
- A real value edit (project_key) is preserved.

## Anti-regression
- Tests: clean stamp-only emkeel.toml; keep a project_key edit; existing hand-edit-preserved test still passes.
