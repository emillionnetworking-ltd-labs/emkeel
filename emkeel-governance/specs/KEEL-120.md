# KEEL-120 — emkeel jira describe: set/replace an existing ticket's description

Strategy: none

## Context
`emkeel jira` can set a description only at create (`--description`); there is no command to edit an
EXISTING ticket's description. An em-ecosystem agent hit this and worked around it by stashing
execution guidance in MEMORY (the weakest, non-binding, per-instance layer) — a flaw: the source of truth
for ticket detail is the on-disk spec, mirrored on the ticket, not memory. Fix the tool, not the symptom:
add a command to write a description, so guidance lives on the ticket (mirroring its spec). Small CLI
addition reusing existing machinery (the PUT already used for labels, the ADF builder from create) — no new
architectural decision, hence no ADR and `Strategy: none`.

## Plan
1. **`_adf(text)`**: plain text → Atlassian Document Format (one paragraph per line — ADF text nodes can't
   hold newlines; blank lines preserved). Refactor `create_issue` to use it (single source).
2. **`set_description(key, text)`**: `PUT /rest/api/3/issue/{key}` with `fields.description = _adf(text)`
   (same PUT path `_unmark_pending` already uses).
3. **`emkeel jira describe <key> (--text "…" | --from <file>)`**: isolation-guarded + creds-checked (like
   `place`); reads text inline or from a file; reports success/HTTP error.
4. Tests (unit + integration) + bump 0.1.103.

## Acceptance Criteria
1. `set_description` PUTs a `doc`-typed ADF to `/rest/api/3/issue/{key}`; multi-line text becomes multiple
   paragraphs; an HTTP error returns `(False, msg)` with the status.
2. `emkeel jira describe <key> --text "…"` updates the description (exit 0); `--from <file>` reads the text
   from a file; `--text`/`--from` are mutually exclusive and one is required.
3. A cross-project key is refused by the isolation guard (exit 1); missing creds → error + exit 1 (no PUT).
4. `create_issue` still works (refactored onto `_adf`); existing jira/create tests stay green.
5. Real end-to-end integration test: CLI args → the actual ADF PUT body, and the isolation block. Bump
   0.1.103; all tests pass.
