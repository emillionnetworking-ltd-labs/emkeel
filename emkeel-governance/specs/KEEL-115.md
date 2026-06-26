# KEEL-115 — check_strategy_process allows retiring a strategy (delete doc + sidecar as a pair)

Strategy: none

## Context
`check_strategy_process` assumes every touched `<topic>.md` must still carry its `<topic>.process.json` at
`≥checked`. So **retiring** a strategy — deleting the doc and its sidecar to remove a path that did not work
— FAILs: the gate iterates the changed `.md` (including deletes, via `git diff --name-only`), looks for each
sidecar on disk, and reports "governed-process state missing" because the sidecar is gone. A governed
process could be completed but never *ended*. This adds the missing operation: a clean retiro is OK, while
the orphan (doc gone, sidecar alive) stays a FAIL. Standalone gate semantics, decided in ADR-0010 — hence
`Strategy: none`.

## Plan
1. **`deleted_files(base)`** (in `check_maint_scope`, beside `changed_files`): the deletes in the PR diff via
   `git diff --diff-filter=D --name-only` — `--name-only` alone can't tell a delete from an edit.
2. **`check_doc(..., retired=bool)`**: when the `.md` is being deleted, a present sidecar → FAIL (orphan); an
   absent sidecar → OK (clean retiro). The add/edit path is untouched (still `≥checked` with provenance).
3. **`main()`** computes the deleted set and passes `retired = md in deleted` per doc; a retiro prints its own
   OK line.
4. **`/strategy` skill** gains a one-line "Retiring one?" note (delete the pair, in a `strategy/<KEY>` lane);
   the self-installed `SKILL.md` is regenerated.
5. **ADR-0010** recording the retiro contract. Integration test (`gates/*` is critical surface). Bump 0.1.98.

## Acceptance Criteria
1. **Clean retiro**: a PR that DELETES `<topic>.md` and `<topic>.process.json` together → OK (no FAIL).
2. **ADD/EDIT stays strict**: an added/modified strategy still requires its sidecar at `≥checked` with
   `researched` provenance — nothing weakened (existing tests stay green).
3. **Anti-orphan**: `<topic>.md` deleted while the sidecar survives → FAIL (a process without its doc).
4. The two real strategies (`satellites`, `satellite-builders`) retire in one atomic PR (both pairs deleted)
   → OK.
5. Real-git integration test covers the clean retiro (PASS) and the orphan (FAIL) through actual
   `--diff-filter=D`. Bump 0.1.98; all tests pass.
