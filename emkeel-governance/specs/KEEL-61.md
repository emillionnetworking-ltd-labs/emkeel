# KEEL-61 — CI warns on stale wiring every PR (drift-based) — doctor isn't enough (opt-in)

## Context
`emkeel doctor` only nudges if the user runs it. Surface stale wiring where it can't be missed:
the CI gate, which runs on every PR and is installed via `pip install emkeel` (live), so it reaches
every repo even with an old workflow YAML.

## Plan
- `src/emkeel/update.py` — `wiring_drift(target)`: generated files whose committed content differs
  from current templates (excludes emkeel.toml stamp + append-only files).
- `src/emkeel/gates/check_ticket_link.py` — `_warn_if_stale_wiring()` emits a non-blocking
  `::warning::` when drift exists (lives in a gate the CI already runs → reaches all repos).
- `src/emkeel/doctor.py` — use `wiring_drift` (precise; replaces the version-compare nudge).
- Tests across update/doctor/gate. Bump 0.1.47.

## Acceptance Criteria
- A PR on a repo with drifted wiring shows a CI warning telling the user to run `emkeel update`.
- No warning when the wiring matches current templates (drift-based, not per-version → no noise).
- doctor reports drift precisely; the gate never fails because of the nudge.

## Anti-regression
- Tests: drift clean after apply; drift detects a stale file; toml stamp ignored; gate warns on drift
  and is silent when current.
