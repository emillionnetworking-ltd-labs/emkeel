# 8. Governance-doc conventions: canonical English fields + bidirectional ADR supersession

- Status: accepted
- Date: 2026-06-25
- Deciders: operator (EMillion Networking)
- Ticket: KEEL-109

## Context

Every emkeel gate parses inline `Field:` lines by an **English** field name — the strategy-link gate
matches `^\s*Strategy:` (`src/emkeel/gates/check_strategy_link.py:20`), the acceptance-criteria gate matches
an English heading (`src/emkeel/gates/check_acceptance_criteria.py:18-37`). When a doc writes the key in
another language (`Estado:` instead of `Status:`), the regex matches nothing and the gate reads "field
absent" — a **silent false negative**, not an error. That is the lived incident: a per-language status check
"saw" ADRs with no status. The parser cannot tell "field missing" from "field in the other language".

Separately, ADR supersession was **forward-only and unenforced**: no ADR expressed supersession and no gate
checked it, so reading any one ADR you could not tell whether it was still live.

The strategy `governance-doc-conventions` (Option 2, approved) decided the fix: keep emkeel's inline
`Field:` idiom, make the keys a canonical English contract, and enforce both the keys and the supersession
backlink with a gate — turning a suggestion into a mechanical check, the `check_critical_integration`
(KEEL-103) / governed-process (KEEL-104) spirit.

## Decision

**1. The three-register language rule.** A governed doc (ADR / strategy / spec) is written in three registers:
- **Field NAMES (keys the machine parses):** canonical **English**, fixed vocabulary — `Status:`, `Date:`,
  `Deciders:`, `Ticket:`, `Supersedes:`, `Superseded-by:`, `Strategy:`, `Acceptance Criteria`. Keys are
  stable identifiers, never localized.
- **PROSE (Context / Decision / Consequences):** the author's **natural language** — humans write content
  in theirs.
- **CODE / identifiers (enum values, slugs, ADR refs, ticket keys):** canonical **English/stable tokens** —
  `accepted`, `superseded`, `ADR-0007`, `KEEL-109` — machine values, part of the parsed contract.

**2. The ADR field contract.** Every ADR carries `Status:`, `Date:`, `Deciders:` (`Ticket:` recommended).
`Status` ∈ `{proposed, accepted, rejected, deprecated, superseded}` (MADR-grounded).

**3. Bidirectional supersession.** Supersession is recorded on **both** records: `Supersedes: ADR-Y` in
ADR-X ⇔ `Superseded-by: ADR-X` in ADR-Y, and the superseded ADR-Y's `Status` becomes `superseded`. So
"is this ADR still live?" is answered by reading the ADR itself — no forward-only dead ends.

**4. The gate `check_doc_conventions`** (`src/emkeel/gates/check_doc_conventions.py`) enforces 1–3:
- **The language rule (1) applies to EVERY governed artifact** (KEEL-110): the gate scans every `*.md`
  under `emkeel-governance/` recursively — adr, strategy, specs, records, and **any future artifact type or
  subdir, covered by default** — and FAILs on a banned localized field key (`Estado:`/`Estrategia:`/…) or a
  banned localized section heading (`## Criterios de Aceptación`/`## Alineación`) naming the canonical
  English key. So the silent-miss can't slip into a non-ADR artifact, and generalizing never leaves a
  per-type gap again.
- **The structural rules (2–3) are ADR-scoped** (they are an ADR contract): **required canonical fields**
  present (`Status`/`Date`/`Deciders`), **Status enum** checked, and **bidirectional supersession** — a
  one-way link, a non-`superseded` target, or a missing target → FAIL. ADRs are scanned together because
  bidirectionality is a cross-file graph property.
- **Dormant** when there is no governance dir or it holds no docs. Shipped to every governed repo's CI by
  `emkeel init`.

## Consequences

- The silent language-split false negative is structurally impossible to merge: a localized key is a loud
  CI failure, not an absence.
- Any ADR's liveness is self-evident from its own fields; a supersede that forgets the backlink fails CI.
- Existing ADRs already satisfy the field contract (English keys, `Status: accepted`), so there is no
  migration — the gate is additive and green on day one.
- The inline-`Field:` idiom is preserved (no frontmatter fork); prose stays in the author's language.
- Trade-off accepted: the inline regex remains the parse surface (a theoretical CRLF-class brittleness)
  rather than a structured frontmatter parser — judged not worth forking emkeel's idiom and rewriting every
  governed repo's ADRs (the rejected Option 3).
