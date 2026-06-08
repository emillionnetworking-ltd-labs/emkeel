# KEEL-51 — verify Jira credentials before saving the secret

## Context
`emkeel connect` stored the Jira email+token via `gh secret set` without checking them. Wrong
credentials would be accepted silently and only fail later (post-merge transition). Validate them.

## Plan
- `src/emkeel/connect.py` — `verify_jira(base_url, email, token)` calls `GET /rest/api/3/myself`
  with Basic auth (`_jira_fetch`, resolved at call time for testability). In the secrets step, loop:
  read email+token → verify → on success show the display name + save; on failure warn (HTTP code),
  do NOT save, offer retry. `tests/test_connect.py`. Bump 0.1.35.

## Acceptance Criteria
- Before saving, connect verifies the email+token against Jira; invalid creds are NOT saved and the
  user is told (with the HTTP code) and offered a retry.
- Valid creds are confirmed (display name shown) and saved.

## Anti-regression
- Tests: verify_jira valid/invalid (injected fetch); secrets not saved when login fails.
