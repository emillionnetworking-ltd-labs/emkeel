# KEEL-62 — Config concordance: warn when branch ticket key project != emkeel.toml project_key

## Context
A repo can drift between its declared `project_key` (emkeel.toml) and the project actually being
worked (branch ticket keys) — e.g. toml says SCRUM but work moves to ECO. Auto-detect it WITHOUT
needing `emkeel doctor`: surface it on every PR via the gate (which already runs + has the key).

## Plan
- `src/emkeel/gates/check_ticket_link.py` — `_warn_if_project_mismatch(key)`: compare the key's
  project prefix to emkeel.toml [jira] project_key; non-blocking `::warning::` on mismatch.
- `src/emkeel/doctor.py` — gather reads jira_project + current branch key; report_lines warns on mismatch.
- Tests. Bump 0.1.48.

## Acceptance Criteria
- A PR whose branch key project differs from emkeel.toml project_key shows a CI warning (non-blocking).
- doctor warns on the same mismatch; silent when they match.

## Anti-regression
- Tests: gate warns on ECO-1 vs SCRUM, silent on SCRUM-9 vs SCRUM; doctor warns/silent likewise.
