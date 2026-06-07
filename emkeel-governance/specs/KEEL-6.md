# KEEL-6 — jira-transition Action (auto-close on merge)

## Context
Closes the loop's last manual step: today the ticket is moved to Done by hand via REST.
A post-merge GitHub Action transitions the linked ticket automatically. It ships with
Emkeel and is scaffolded by `emkeel init`, so every governed repo gets it. NOT a gate —
runs after merge, non-blocking.

## Plan
- `src/emkeel/jira.py` — `pick_transition()` + `transition_issue()` (injectable HTTP) + CLI.
- `tests/test_jira.py` — logic tested with an injected caller (no network) + `main()`.
- `.github/workflows/jira-transition.yml` — runs `python -m emkeel.jira` on PR merge.
- `src/emkeel/init.py` — scaffolds the same workflow into governed repos.

## Acceptance Criteria
- On a merged PR, the linked ticket (key from the branch/PR title) is transitioned to Done.
- `transition_issue` is unit-tested with an injected HTTP caller — no real network in tests.
- A missing/unavailable transition is a soft success (non-blocking), not a red run.
- Credentials are read from secrets (`JIRA_*`); none are committed.
- `emkeel init` now also scaffolds `jira-transition.yml` into the target repo.

## Anti-regression
- Tests cover: `pick_transition` (found/not-found, case-insensitive), `transition_issue`
  (success, soft-skip, read-fail, post-fail), and `main()` (key from branch, no-key).
