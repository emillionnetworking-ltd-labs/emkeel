# KEEL-66 — Auto-ship by default via a scope-gated emkeel-maint lane

## Context
A `--ship <KEY>` flag (KEEL-65) was forgettable → files left pending. Make shipping the DEFAULT and
keyless, without a real bypass: a maintenance lane the ticket gate accepts only because a scope gate
proves it touches nothing but Emkeel-managed files.

## Plan
- `src/emkeel/ship.py` — keyless `ship(paths)`: forks `emkeel-maint/<ver>-<sha>` from the DEFAULT
  branch (works from any branch), refuses if other files are dirty, commits only the given paths,
  push→PR→auto-merge. Reuses connect.py.
- `src/emkeel/update.py` + `setcfg.py` — ship by DEFAULT when files change; `--no-ship` opts out.
- `src/emkeel/gates/check_ticket_link.py` — accept `emkeel-maint/` branches without a Jira ticket.
- `src/emkeel/gates/check_maint_scope.py` — NEW: an emkeel-maint PR may touch ONLY Emkeel-managed files.
- `src/emkeel/init.py` + `.github/workflows/ci.yml` — `fetch-depth: 0` + wire the scope gate. Tests. Bump 0.1.52.

## Acceptance Criteria
- `emkeel update` / `emkeel set` (no flag) ship the change through `emkeel-maint/*` → PR → auto-merge;
  `--no-ship` leaves files pending.
- check_ticket_link passes an emkeel-maint branch with no ticket; check_maint_scope fails it if the
  PR touches any non-Emkeel file.
- ship forks from the default branch and refuses when unrelated changes are dirty.

## Anti-regression
- Tests: ship full-flow/refuse-stray/no-op; maint-scope na/ok/stray; ticket-link accepts maint;
  update+set ship-by-default vs --no-ship; CI wires the scope gate + fetch-depth.
