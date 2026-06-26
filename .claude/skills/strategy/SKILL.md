---
name: strategy
description: >
  Research and decide a development/engineering strategy for a topic (a module, security, a
  technology choice, an approach…). Produces a grounded, sourced strategy doc, driven through
  emkeel's governed-process engine — the steps are NON-SKIPPABLE. Use when you must choose the
  right path and want it researched, not guessed.
---

# /strategy <topic>

Produce a RESEARCHED strategy for `<topic>`, persisted at `emkeel-governance/strategy/<topic>.md`.
**Every claim must cite a real source (file:line in the repo, or a URL) gathered with TOOLS — never
from memory. Never invent an option or a source.**

This skill is a state machine, not advisory prose. After each step's real work, record it with
`emkeel strategy advance <step> <topic> --set <evidence>` — the engine REFUSES an out-of-order or
evidence-less advance (exit 1), and CI (`check_strategy_process`) fails the PR unless the committed
`<topic>.process.json` reached `validated` (the strategy was tried on a real case) with real research
provenance. `emkeel strategy status <topic>` shows where you are. Run each `advance` ONLY after that step's
work is done.

1. **Scaffold** — `emkeel strategy new <topic>` creates the structured doc; declare up front the
   **kill-criteria** (what would prove this strategy WRONG — the conditions under which to abandon it):
   `emkeel strategy advance scaffolded <topic> --set=topic=<topic> --set='kill_criteria=[<cond1>,<cond2>,…]'`
2. **Research** (ground in reality; fan out with subagents):
   - *Repo:* Read/Grep the actual code & config for `<topic>` — what exists, conventions, constraints. Cite `file:line`.
   - *Market:* WebSearch/fetch real options & trade-offs. Cite URLs.
   Record the provenance — the engine and CI REFUSE `researched` without it:
   `emkeel strategy advance researched <topic> --set='sources=[<url>,<file:line>,…]'`
   If `<topic>` genuinely has no market/external dimension, declare it EXPLICITLY (never skip the web silently):
   `emkeel strategy advance researched <topic> --set=internal_only=true`
3. **Propose** — fill the Options table with **≥2 real options**, each with its **Source**, pros, cons, risk:
   `emkeel strategy advance proposed <topic> --set='options=[<opt1>,<opt2>,…]'`
4. **Critique** (adversarial; subagents): for each option a skeptic **re-opens the cited source** — does it
   really say that? — and attacks weaknesses + drift risks. Drop/fix anything unverified, then:
   `emkeel strategy advance critiqued <topic> --set=critique="<what the adversarial pass found / fixed>"`
5. **Check** — run `emkeel strategy check <topic>` and fix until it passes (green = sourced + complete). Then:
   `emkeel strategy advance checked <topic> --set=check_passed=true`
6. **Validate against reality** — apply the recommendation to ONE real case (cheap is fine: try it once and
   look at the result). Record the case, how you tested it, the **outcome** (`pass` | `fail` | `mixed`), and a
   **resolvable proof** (a repo `file:line`, a URL, or an external citation). The engine and CI REFUSE
   `validated` without it — reality is non-skippable, and a `fail`/`mixed` is an HONEST record, never hidden:
   `emkeel strategy advance validated <topic> --set=case="<the real case>" --set=method="<how you tested>" --set=outcome=<pass|fail|mixed> --set=evidence_ref=<file:line|URL>`
7. **Human gate — present** — present the options + your recommendation to the operator. **Do NOT decide
   for them.** Record that you showed it (this does NOT approve anything) — the LAST step you commit in the
   lane PR. If the reality outcome was `fail`/`mixed`, proceeding requires a recorded `proceed_justification`
   — approving despite a failed reality test must be a deliberate, on-record act:
   `emkeel strategy advance presented <topic> --set=presented_to=<operator>`
   (add `--set=proceed_justification="<why proceed despite the reality result>"` when the outcome was not `pass`)
8. **Approval is the MERGE — never stamp it yourself.** The operator approves by **approving + merging the
   PR** (branch protection requires a human approving review). Do NOT run `emkeel strategy advance approved`
   in the lane PR — a self-written `approved_by` certifies nothing, and the `check_strategy_process` gate
   FAILS a committed `approved` (the merge hasn't happened yet). The committed `<topic>.process.json` stops
   at `presented`; the merge IS the approval, recorded immutably in the PR/git history.
   On the operator's yes, set `Status: APPROVED` in the doc, finalize the Recommendation, offer to record
   the decision as an ADR in `emkeel-governance/adr/`, and remind them to add `Strategy: <topic>` to
   feature specs (the `check_strategy_link` gate enforces it).

**Refining an existing strategy?** A new refinement (a new ticket on the same `<topic>`) starts the process
CLEAN — re-run from `scaffolded`; the engine resets and a prior refinement's `approved` NEVER carries over.

**Retiring a strategy?** A path that didn't work can be withdrawn: in a `strategy/<KEY>-slug` lane (with a
ticket), DELETE `<topic>.md` AND its `<topic>.process.json` together — as a pair. The gate accepts a clean
retiro; deleting the doc while leaving the sidecar (or vice versa) is an orphan → FAIL.

**Commit `emkeel-governance/strategy/<topic>.process.json` alongside the doc** — it is the proof the steps
ran, and CI reads it. `emkeel strategy status <topic>` shows ✓/· per step. Never skip the human gate
(presenting + the merge are the operator's). Never cite a source you didn't open.
