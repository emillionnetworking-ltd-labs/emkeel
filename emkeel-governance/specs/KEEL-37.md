# KEEL-37 — emkeel doctor (setup health check)

## Context
After `emkeel setup`/`init`, several steps are the user's (Jira token, GitHub secrets, branch
protection). If they forget, things silently don't work. `emkeel doctor` makes the state
visible on demand: what's done, what's pending, with the exact fix links. New-project aware.

## Plan
- `src/emkeel/doctor.py` — `gather()` inspects emkeel.toml + GitHub remote + `gh` auth + Jira
  secrets + `gates` required; `report_lines()` renders PASS/MISSING with links. If no remote →
  "create + push the repo first" (skip gh checks). `src/emkeel/cli.py` dispatch `doctor`.
- `tests/test_doctor.py`. Bump 0.1.21.

## Acceptance Criteria
- `emkeel doctor` reports: governed? · connected to GitHub? · gh authed? · Jira secrets set? ·
  `gates` required? — each PASS/MISSING with a fix link.
- With no GitHub remote, it says to create + push the repo first and does not assert secrets/protection.
- It exits 0 (informational); a "pending" summary lists remaining steps.

## Anti-regression
- Tests cover report_lines for: not-governed, not-connected, no-gh, all-good, and pending-with-links.
