# KEEL-71 — doctor concordance reads project_key from origin/<default>

## Context
Consistent with KEEL-68 (wiring measured vs origin). The branch-vs-project warning read the LOCAL
emkeel.toml, so after `emkeel set` ships a new project_key to main, the warning persisted on a
feature branch (which still declares the old key) until merge.

## Plan
- `src/emkeel/update.py` — `origin_jira_project(target)`: project_key from origin/<default>:emkeel.toml
  (local fallback when no remote).
- `src/emkeel/doctor.py` — gather uses it for `jira_project`. Tests. Bump 0.1.57.

## Acceptance Criteria
- doctor's concordance compares the current branch key to origin/<default>'s project_key, so once
  `emkeel set jira-project ECO` merges to main, the warning clears on any branch.
- Local fallback when there's no remote.

## Anti-regression
- Tests: origin_jira_project reads origin over a stale local branch; local fallback with no remote.
