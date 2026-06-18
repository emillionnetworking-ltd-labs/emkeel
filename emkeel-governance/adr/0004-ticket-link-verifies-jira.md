# 4. The ticket-link gate verifies existence in Jira (a gate may consult Jira in CI)

- Status: accepted
- Date: 2026-06-18
- Deciders: operator (EMillion Networking)
- Ticket: KEEL-83

## Context

Emkeel's gates are deterministic and, until now, **offline/hermetic** — they read the repo and the
branch/PR, nothing else. `check_ticket_link` was therefore purely syntactic: it matched `KEY_RE`
(`ECO-12`) but could not tell whether the ticket existed. In practice this let a whole run of tickets
(ECO-19/20/21, KEEL-78..82) merge while never existing in Jira — the "ticket→code" link pointed at
nothing. A syntactic check is a suggestion; the traceability it claims is only real if the ticket exists.

The honest fix is for the gate to ask Jira. That breaks the "gates are offline" property, so it is a
deliberate architectural decision, not an implementation detail.

## Decision

The `check_ticket_link` gate **may make a single, read-only Jira call** (`GET /rest/api/3/issue/{key}`)
when the Jira secrets are present, and **FAILS on a 404**. Specifically:

- **Secrets present + 404** → hard fail (the new line of defense).
- **Secrets present + 200** → pass.
- **Secrets absent** → non-blocking warning, syntax-only pass (the gate stays usable offline, on forks,
  and before secrets are configured — the same graceful degradation the post-merge transition already uses).
- **Secrets present + non-404 error (auth/5xx)** → inconclusive, non-blocking warning (a transient Jira
  hiccup must not block a merge; the hard fail is reserved for an unambiguous "does not exist").

The `emkeel-maint/*` lane remains exempt (no ticket, no Jira call). The HTTP layer stays injectable so the
decision logic is unit-tested without network. The verification reuses `jira._http_caller` /
`secrets_present()` — one HTTP boundary for the whole tool.

## Consequences

- **The ticket→code link becomes real**, not just well-formed: a nonexistent key can no longer merge when
  secrets are configured. This is the intended hardening.
- **Gates are no longer strictly offline.** This is scoped to ONE gate making ONE read-only call, gated on
  secrets, degrading to the previous syntactic behavior when they're absent — so determinism is preserved
  where it matters (no secrets ⇒ identical to before) and the network dependency can never *silently*
  weaken the gate (404 is the only blocking outcome; everything ambiguous warns).
- **Convenience to satisfy the gate**: `emkeel jira create` (mirror of the transition helper) lets a flow
  create a missing ticket in one line — the gate stays the hard line, creation is just the ergonomics.
- **Post-merge transition is now verified**: `transition_issue` reads the status back and a real
  "didn't reach Done" surfaces (the blind `continue-on-error` is removed). Benign "already Done" is
  confirmed rather than assumed.
- Trade-off accepted: a CI run now depends on Jira reachability for the *blocking* path only when secrets
  are set; transient errors degrade to warnings by design.
