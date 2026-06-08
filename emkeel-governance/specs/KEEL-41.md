# KEEL-41 — doctor recognizes 'gates' required via Rulesets too

## Context
`emkeel doctor` checked only the classic `branches/{b}/protection` endpoint, which returns 404
when branch protection is configured via a **Ruleset** (the newer GitHub mechanism). That made
doctor report a false "✗ gates required" even when a ruleset enforced it.

## Plan
- `src/emkeel/doctor.py` — add `_gates_required(repo, branch, run=_run)` that returns True if
  'gates' is required via **classic** protection OR a **ruleset** (`rules/branches/{b}`). Use it
  in `gather`. Make `run` injectable for unit tests. `tests/test_doctor.py`. Bump 0.1.25.

## Acceptance Criteria
- doctor reports 'gates' required when enforced via classic branch protection OR via a ruleset.
- It reports not-required only when neither mechanism requires 'gates'.

## Anti-regression
- Tests cover `_gates_required` for: classic-only, ruleset-only (classic 404), and neither.
