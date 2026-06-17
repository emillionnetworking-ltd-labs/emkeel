# KEEL-82 — `doctor` verifies branch protection enforces the required checks the repo DECLARES

## Context
A check that *exists* but isn't *enforced* is not a gate. em-ecosystem's Security Pipeline ran on every PR
but was **not a required check** in branch protection → PRs merged with security red. It was fixed by hand
(adding "Security Gate (All Checks)" to required). This generalizes that fix: a repo declares which checks
must be required, and `emkeel doctor` detects the drift when one isn't enforced.

`doctor` already verifies the `gates` check is required (classic protection OR ruleset). This extends that
to a declared list. It stays in `doctor` — not a CI gate — because reading branch protection from inside CI
is fragile (token scope, circularity); `doctor` runs locally with the operator's `gh` (which has the scope).

## Plan
- `emkeel.toml` declares the required checks under `[github]`:
  ```toml
  [github]
  repo = "..."
  required_checks = ["gates", "Security Gate (All Checks)"]
  ```
  - `Config.required_checks` parses it (stdlib `tomllib`); absent key → default `["gates"]` (backward-compat).
  - `gates` is ALWAYS verified even if not in the list (emkeel's own, non-negotiable): effective set =
    `{"gates"} ∪ required_checks`.
- `doctor` — generalize `_gates_required` → `_required_contexts(repo, branch)` returning the SET of enforced
  contexts (classic ∪ ruleset; `None` when undeterminable so the caller shows `?`). Then: `declared = {"gates"}
  ∪ required_checks`; `missing = declared − enforced`. Empty → OK (lists the enforced extras); non-empty →
  drift, each with the exact fix `gh api -X POST repos/<repo>/branches/<branch>/protection/required_status_checks/contexts -f 'contexts[]=<check>'`.
- `init.py` — scaffold `emkeel.toml` with a COMMENTED `required_checks` example (default `gates`) + a setup-
  checklist line explaining that declaring extra checks makes `doctor` verify their enforcement.
- Tests (gh mocked); bump 0.1.68.

## Invariants
- A repo WITHOUT the `required_checks` key → only `gates` is verified → behavior identical to today (emkeel's
  own doctor is unchanged — emkeel only has `gates`).
- Supports classic protection AND rulesets (both paths tested), as `_gates_required` did.
- Zero-dep stdlib, deterministic, `_run` injectable for tests. `gh` undeterminable → `?`, never a crash.

## Auto-publish note
Auto-publish is ACTIVE (KEEL-81). On MERGE, the push to `main` will publish **0.1.68** to PyPI automatically;
the workflow is idempotent (it only publishes a version whose `v<version>` tag is absent).

## Acceptance Criteria
1. Declared `required_checks` all enforced → doctor OK (lists them).
2. A declared `required_check` not enforced → doctor reports drift + prints the exact `gh api` fix.
3. No `required_checks` key → only `gates` verified (backward-compat).
4. `gates` is always verified, even when not in the declared list.
5. Works with classic protection AND with a ruleset (both paths tested).
6. `gh` unavailable/undeterminable → `?`, no crash.
7. Coverage maintained (≥85% branch / ≥90% line on changed files).
