# KEEL-109 — implement governance-doc-conventions: check_doc_conventions + ADR-0008

Strategy: governance-doc-conventions

## Alignment
Implements the approved Option 2 of the `governance-doc-conventions` strategy (canonical English inline
fields + a hygiene gate), recorded as ADR-0008. It realizes the strategy's three-register language rule, the
ADR field contract, and bidirectional supersession — and enforces them mechanically (the
`check_critical_integration` / governed-process spirit: a gate, not a suggestion).

## Plan
1. **`check_doc_conventions`** (new CI gate): scans ALL ADRs under `emkeel-governance/adr/` each run;
   requires canonical English `Status`/`Date`/`Deciders`; `Status` ∈ the MADR enum; bans localized keys
   (`Estado:`/`Fecha:`/`Decisores:`/`Reemplaza:`/`Sustituye:`/…) with a loud FAIL naming the canonical key;
   enforces bidirectional `Supersedes:` ⇔ `Superseded-by:` (superseded target has `Status: superseded`,
   targets exist). Dormant when there is no `adr/` or it is empty.
2. **Wiring** into emkeel's own `ci.yml` and the generated `_ci_yaml` (every governed repo gets it).
3. **ADR-0008** recording the convention (three-register rule + field contract + bidirectional supersession
   + the gate).
4. The strategy doc → `Status: APPROVED`, recommendation finalized, decision linked to ADR-0008.

## Acceptance Criteria
1. A localized field key (`Estado:`) → loud FAIL naming the canonical `Status:` (the lived silent-miss is
   now loud); the canonical key passes.
2. Missing required field / out-of-enum status → FAIL.
3. One-way supersession, a non-`superseded` target, or a missing target → FAIL; a bidirectional pair passes.
4. Dormant without `adr/`; scans all ADRs (cross-file). Shipped into every governed repo's generated CI.
5. All existing ADRs (0001–0008) pass the gate; the gate is unit + integration tested. Bump 0.1.92; all
   tests pass.
