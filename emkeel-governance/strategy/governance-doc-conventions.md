# Strategy: governance-doc-conventions

Status: DRAFT
Strategy: governance-doc-conventions   <!-- feature specs reference this with a `Strategy: governance-doc-conventions` line -->

## Goal
Make every governed doc (ADR / strategy / spec) parse the SAME way for a machine and stay coherent for a human: canonical-language field NAMES the gates can read predictably, plus bidirectional ADR supersession — and ENFORCE both with a gate so the silent language-split never recurs.

## Context
<!-- grounded facts ONLY — cite file:line (repo) or a URL (market) for every claim -->
- **The split is real and the parsing is English-only.** Every emkeel gate parses inline `Field:` lines by an English field name: the strategy-link gate matches `^\s*Strategy:\s*(\S+)` (`src/emkeel/gates/check_strategy_link.py:20`) and the acceptance-criteria gate matches an English heading via `has_section` (`src/emkeel/gates/check_acceptance_criteria.py:18-37`). A doc that writes the field in another language is not matched.
- **Silent miss is the failure mode, by construction.** When the field name doesn't match, the regex returns nothing and the gate reads "field absent" — a false negative, not an error. This is exactly the lived incident: a per-language status check "saw" N ADRs with no status (false). The parser cannot tell "field missing" from "field in the other language".
- **emkeel's own docs already standardize on English keys** — the strategy template emits `Status: DRAFT` (`src/emkeel/strategy.py:43`) and every ADR uses `- Status: accepted` (`emkeel-governance/adr/0001-adopt-and-thin.md:3`). The keys are *already* English everywhere the machine looks; the risk is drift in repos/authors that localize the key.
- **ADR supersession is forward-only today and there is no enforcement.** No ADR in the repo expresses supersession at all, and no gate checks it (grep across `emkeel-governance/adr/` and `src/`: no `supersede`/`superseded-by`/`replaces`). Reading any one ADR, you cannot tell whether it is still live.
- **emkeel already has the enforcement shape for "make the discipline mechanical, not a suggestion".** `check_critical_integration` turns a lesson into a gate that FAILS the PR rather than a doc that asks nicely (`src/emkeel/gates/check_critical_integration.py:1`) — the KEEL-93/94/103/104 spirit this strategy must follow.
- **A cross-file gate that lints ALL docs each run is precedented.** `check_strategy_quality` lints every `strategy/*.md` on every PR, not just changed ones — the right model for a backlink invariant, which is a graph property across files. The diff helper `changed_files(base)` exists if a scoped scan is ever wanted (`src/emkeel/gates/check_maint_scope.py:29`).
- **Gates are cheap to add and already chained in CI** — each is one workflow step `python -m emkeel.gates.check_*` with `EMKEEL_BRANCH`/`EMKEEL_BASE_REF` injected (`src/emkeel/init.py:286-346`), shipped into every governed repo by `emkeel init`. The quality gate resolves each `file:line` source (file exists + line in range) so this very doc is fact-checked in CI (`src/emkeel/strategy.py:8`).
- **Market — the convention this repo is missing is the documented norm.** MADR encodes status as a fixed English enum and writes supersession as a value on the superseded record: `status: "{proposed | rejected | accepted | deprecated | … | superseded by ADR-0123}"` (https://raw.githubusercontent.com/adr/madr/main/template/adr-template.md). adr-tools makes supersession BIDIRECTIONAL by construction — `adr new -s 9` creates the new ADR flagged "supercedes 9" AND edits ADR 9 to "superceded by" the new one (https://github.com/npryce/adr-tools/blob/master/README.md).
- **Market — keys stay canonical, values get localized.** The established i18n principle: a key is a stable identifier, not display text — "Keep key names stable, even if the translation value changes later" (https://lokalise.com/blog/translation-keys-naming-and-organizing/). Frontmatter is the ecosystem's machine-readable metadata layer with structured key/value parsing (https://gohugo.io/content-management/front-matter/); MADR specifically moved status into YAML frontmatter rather than an inline `Status:` line (https://raw.githubusercontent.com/adr/madr/main/template/adr-template.md).

### The three-register language rule (the actual "what goes in which language" decision)
Independent of which option below is chosen, the convention names three registers:
1. **Field NAMES (keys the machine parses):** canonical **English**, fixed vocabulary — `Status:`, `Date:`, `Deciders:`, `Ticket:`, `Supersedes:`, `Superseded-by:`, `Strategy:`, `Acceptance Criteria`. (i18n: keys are stable identifiers — lokalise; MADR uses English keys.)
2. **PROSE (Context / Decision / Consequences body):** the author's **natural language** — humans write the content in theirs.
3. **CODE / identifiers (enum values, slugs, ADR refs, ticket keys):** canonical **English/stable tokens** — `accepted`, `superseded`, `ADR-0007`, `KEEL-103` — they are machine values, part of the parsed contract, never `aceptado`.

## Options
<!-- at least 2 real options; EVERY row MUST cite a Source (file:line or URL). `emkeel strategy check` enforces it. -->
| # | Option | Source | Pros | Cons | Risk |
|---|--------|--------|------|------|------|
| 1 | **Style guide only** — write the three-register rule + bidirectional supersession into AGENTS/an ADR; no machine check | src/emkeel/gates/check_critical_integration.py:1 | Zero code; documents intent | It is a suggestion — the same class the engine exists to kill; nothing stops a localized key or a one-way supersede; recurs silently | HIGH — false negatives keep slipping through; the incident repeats |
| 2 | **Canonical English inline fields + a hygiene gate** (recommended) — keep the existing inline `Field:` format, add `check_doc_conventions`: required canonical English fields present, status in the enum, banned localized keys (`Estado:`/`Fecha:`/`Decisores:`) FAIL loud, supersession must be bidirectional | src/emkeel/gates/check_strategy_link.py:20 | Matches emkeel's entire inline-parsing idiom; converts silent-miss → loud-fail; smallest migration (keys already English); enforces the backlink mechanically | Inline regex stays the parse surface (theoretical CRLF-class brittleness); one more gate to maintain | LOW — additive, dormant when no `adr/`; banned-key rule directly prevents recurrence |
| 3 | **Migrate to YAML frontmatter + a schema gate** — move ADR metadata into MADR-style frontmatter (`status:`, `supersedes:`, `superseded-by:`), gate parses structured frontmatter | https://raw.githubusercontent.com/adr/madr/main/template/adr-template.md | Most robust parsing; loud structural failure; aligns with MADR/Hugo norm; future-proof | Rewrites every ADR in every governed repo; splits emkeel's idiom (all other gates parse inline); still needs the gate for enum + bidirectionality | MEDIUM — large migration for marginal gain over a strict Option-2 gate; idiom fork |

## Recommendation
**Option 2 — canonical English inline fields + a hygiene gate.** The lived bug was NOT inline-vs-frontmatter; it was the **language split** (`Estado:` vs `Status:`) producing a silent false negative. The fix that matters is converting *silent-miss* into *loud-fail*: a gate that REQUIRES the exact canonical English key and FAILS when a known localized key is used instead. Option 2 delivers that while matching emkeel's existing inline-`Field:` idiom (every current gate parses that way — `check_strategy_link.py:20`), with the smallest migration (the keys are already English in our own docs). Option 3's only real advantage over a strict Option-2 gate is CRLF-class regex robustness — minor, and not worth forking the idiom and rewriting every governed repo's ADRs. Option 1 is the exact failure class (a suggestion) that `check_critical_integration` already taught us to reject.

**The gate — `check_doc_conventions` (the enforcement, KEEL-104/105 spirit):**
- **Scans ALL ADRs each run** (like `check_strategy_quality` lints all strategy docs) — bidirectionality is a cross-file graph property; a scoped diff scan would let editing X silently break Y's backlink.
- **Required canonical fields** present on every ADR: `Status:`, `Date:`, `Deciders:` (`Ticket:` recommended). Missing → FAIL.
- **Status enum** ∈ `{proposed, accepted, rejected, deprecated, superseded}` (MADR-grounded). Out-of-enum → FAIL.
- **Banned localized keys** — `Estado:`/`Fecha:`/`Decisores:`/`Reemplaza:` where a canonical key belongs → FAIL with "use canonical English field name `Status:`". This is the precise anti-recurrence rule: a doc with a localized key cannot merge.
- **Bidirectional supersession** — every `Supersedes: ADR-Y` in ADR-X requires `Superseded-by: ADR-X` in ADR-Y (and the reverse), Y's status must be `superseded`, and both targets must exist. A one-way link → FAIL. So "is this ADR still live?" is answered by reading the ADR itself.
- **Dormant** when there is no `emkeel-governance/adr/` or it is empty — repos without ADRs are unaffected. Shipped to every governed repo via `emkeel init` (`src/emkeel/init.py:286-346`), unit + integration tested in the existing idiom.

## Non-goals
- **Not translating prose or forcing English on humans** — body content stays in the author's language (register 2); only keys and code tokens are canonical.
- **Not a full frontmatter migration** (Option 3) — out of scope unless a future need outweighs the idiom fork.
- **Not retrofitting historical ADRs' prose** — the gate enforces fields/supersession going forward; it does not rewrite past Context sections.
- **Not auto-generating ADRs** — authoring stays manual; the gate only refuses inconsistent ones.

## Decisions
<!-- optional: link the chosen decision as an ADR, e.g. emkeel-governance/adr/007-<slug>.md -->
<!-- On approval: record as emkeel-governance/adr/0008-governance-doc-conventions.md (canonical fields + three-register language rule + bidirectional supersession + the check_doc_conventions gate). -->
