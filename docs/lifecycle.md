# Lifecycle (lean)

```
branch  →  artifacts  →  PR  →  gates  →  merge
```

| Step | Artifact | Gate (server-side, non-falsifiable) |
|---|---|---|
| plan | `emkeel-governance/specs/<KEY>.md` (features only) | CI: exists + valid |
| develop | code + tests | CI: lint + types + **full suite** green |
| verify | (CI) + your review | required check + required approval |
| decision | `emkeel-governance/adr/NNNN-*.md` | CI: ADR present if a flagged area is touched |
| merge | — | branch protection: CI green + approval + linked ticket |

## Why it works

- **"done" = the check passes**, not a flag the agent writes. (With and without an engine the
  agent skipped self-attested rules; the orchestrator was never the variable — the locus of
  authority was.)
- The **test suite is the durable memory** against regressions: the agent forgets between
  sessions, the suite does not. Re-breaking something old = CI red = blocked.
- What can't be mechanized is covered by **your human gate** (approving the PR), not more prose.
