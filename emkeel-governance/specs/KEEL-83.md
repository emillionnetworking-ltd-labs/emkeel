# KEEL-83 — Ticket↔Jira traceability: the gate verifies EXISTENCE (+ `emkeel jira create` + verified Done)

## Context
`check_ticket_link` was **syntactic** — `KEY_RE` only checked the branch/PR looked like `ECO-12`, not
that the ticket EXISTED. Result: ECO-19/20/21 and KEEL-78..82 merged without ever being created in Jira
(ECO had 1-18, KEEL had 1-77). Separately, `jira.py` only transitioned (couldn't create), and the
post-merge transition (`jira-transition.yml`) was `continue-on-error: true` + soft-success, so a real
"didn't reach Done" failure was swallowed silently.

`Strategy: none` — this is a governance/traceability hardening, not a product feature serving a strategy.

## Plan
1. **`check_ticket_link` verifies existence.** When the Jira secrets are present, the gate does
   `GET /rest/api/3/issue/{key}` (reusing `jira._http_caller` + `secrets_present()`) and **FAILS on 404**.
   The Jira secrets are wired into the `gates` workflow (`ci.yml` + scaffolded `_ci_yaml`). The
   `emkeel-maint/*` lane stays exempt (no ticket, no Jira call).
2. **`emkeel jira create`** — new thin CLI subcommand + `create_issue(project, summary, issuetype, …)` in
   `jira.py` via `POST /rest/api/3/issue`, returns the new key. The convenience that lets a flow create the
   missing ticket; the gate stays the hard line.
3. **Transition to Done is VERIFIED.** After the POST, `transition_issue` reads the issue back and confirms
   `status == target`. Benign "already Done" is *confirmed* (not assumed); a 404 / failed POST / status that
   didn't land are real failures (ok=False, `::error::`). The blind `continue-on-error` is removed from
   `jira-transition.yml` so real failures surface red.

## Degradation (the trade-off)
- **Secrets present + ticket exists** → PASS. **Secrets present + 404** → HARD FAIL (the new line).
- **Secrets absent** → existence is NOT verified: non-blocking `::warning::`, syntax-only (keeps the gate
  usable offline / on forks without secrets, exactly like the transition automation degrades).
- **Secrets present + non-404 error (auth/5xx)** → inconclusive → non-blocking `::warning::` (don't block a
  merge on a transient Jira hiccup). The hard fail is reserved for an unambiguous 404.

## Invariants
- Every gate change ships with tests. The `emkeel-maint/*` exemption and the benign-transition path are
  preserved (benign "already Done" still succeeds — now verified).
- Zero-dep stdlib; the HTTP layer stays injectable (unit-tested without network).
- Making the gate consult Jira in CI is an architectural shift (gates were offline/hermetic) → see
  `emkeel-governance/adr/0004-ticket-link-verifies-jira.md`.

## Acceptance Criteria
1. Secrets present + ticket exists (200) → gate PASS; + ticket missing (404) → gate HARD FAIL with the fix hint.
2. Secrets absent → non-blocking warning, syntax-only PASS (degradation).
3. Non-404 Jira error → inconclusive, non-blocking PASS (no false block).
4. `emkeel-maint/*` never calls Jira and still passes (exemption intact).
5. `emkeel jira create` creates an issue and returns the key (secrets required; mirror of transition).
6. `transition_issue` verifies the status landed on Done; benign already-Done is confirmed; 404/POST-fail/
   wrong-status are real failures (visible). `jira-transition.yml` has no blind `continue-on-error`.
7. Coverage maintained on touched files.

## Backfill (done out-of-band, REST API)
The 9 missing tickets were created with correct sequential keys and target statuses: ECO-19 (Done),
ECO-20 (In Progress), ECO-21 (Done), KEEL-78..82 (Done), KEEL-83 (Backlog = KEEL's To-Do-equivalent).
