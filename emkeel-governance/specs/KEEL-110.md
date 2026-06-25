# KEEL-110 — generalize ADR-0008 enforcement to ALL governed artifacts

Strategy: governance-doc-conventions

## Alignment
Completes the enforcement of the `governance-doc-conventions` strategy / ADR-0008. The convention's
three-register language rule was only enforced on ADRs; strategy docs, specs, records and any future
artifact relied on the older English-matching gates that do NOT ban the localized key — so the same silent
false-negative could slip there. This realizes ADR-0008's register-1 rule for **every** governed artifact,
and makes the mechanism future-proof so generalizing never leaves a per-type gap again.

## Plan
1. Generalize `check_doc_conventions`: the **universal language rule** (banned localized field keys + banned
   localized section headings → loud FAIL naming the canonical English key) now scans **every `*.md` under
   `emkeel-governance/` recursively** — adr, strategy, specs, records, and any future subdir/type by default.
2. Keep the **ADR-only structural rules** (required fields, status enum, bidirectional supersession) scoped
   to `adr/` — they are an ADR contract.
3. A shared register-1 vocabulary (canonical fields + headings, and their banned localized forms),
   accent-insensitive; reusable `language_problems(text, name)` per doc.
4. Update ADR-0008's enforcement note to reflect the generalized scope.

## Acceptance Criteria
1. A localized inline field key in a **spec** (`Estrategia:`) or **strategy doc** (`Estado:`) → loud FAIL
   naming the canonical key (was silently "absent" before).
2. A localized **section heading** (`## Criterios de Aceptación` / `## Alineación`) in any artifact → FAIL.
3. A **brand-new artifact type** (a new `emkeel-governance/<subdir>/`) with a localized key → FAIL with **no
   code change** (recursive scan covers it by default).
4. ADR structural rules (required fields / enum / bidirectional supersession) still enforced, ADR-scoped.
5. Accent-insensitive matching; dormant without governance docs; all existing artifacts pass. Unit +
   integration tested. Bump 0.1.93; all tests pass.
