# KEEL-56 — emkeel eject --json + playbook asks language first for removal

## Context
When a user told the AI "emkeel eject", it improvised an English scope menu instead of relaying
canonical options in the user's language (it hadn't read the playbook). Give eject a canonical
machine-readable interface and strengthen the playbook.

## Plan
- `src/emkeel/uninstall.py` — `eject_json(target)` + `emkeel eject --json`: bilingual scopes
  (default/purge/all) with flags + present state, like `setup --json`. Forward argv in `__main__`.
- `src/emkeel/_docs/onboarding.md` — removal section: ask language first, then `emkeel eject --json`.
  `tests/test_uninstall.py`. Bump 0.1.41.

## Acceptance Criteria
- `emkeel eject --json` prints 3 bilingual scopes (default/purge/all) + flags, non-interactively.
- The playbook removal flow says: ask language first, then use `emkeel eject --json`.

## Anti-regression
- Tests: eject_json shape/flags; `main([path, "--json"])` prints valid JSON with 3 scopes.
