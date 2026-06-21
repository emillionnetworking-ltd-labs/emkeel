---
name: strategy
description: >
  Research and decide a development/engineering strategy for a topic (a module, security, a
  technology choice, an approach…). Produces a grounded, sourced strategy doc that the gates
  enforce. Use when you must choose the right path and want it researched, not guessed.
---

# /strategy <topic>

Produce a RESEARCHED strategy for `<topic>`, persisted at `emkeel-governance/strategy/<topic>.md`.
**Every claim must cite a real source (file:line in the repo, or a URL) gathered with TOOLS — never
from memory. Never invent an option or a source.**

1. **Scaffold** — run `emkeel strategy new <topic>` to create the structured doc.
2. **Research** (ground in reality; fan out with subagents):
   - *Repo:* Read/Grep the actual code & config for `<topic>` — what exists, conventions, constraints. Cite `file:line`.
   - *Market:* WebSearch/fetch real options & trade-offs. Cite URLs. (No web access? Say so and use the repo only.)
3. **Propose** — fill the Options table with **≥2 real options**, each with its **Source**, pros, cons, risk.
4. **Critique** (adversarial; subagents): for each option a skeptic **re-opens the cited source** —
   does it really say that? — and attacks weaknesses + drift risks. Drop/fix anything unverified.
5. **Check** — run `emkeel strategy check <topic>` and fix until it passes (green = sourced + complete).
6. **Human gate** — present the options + your recommendation to the operator. **Do NOT decide for
   them.** They approve / refine / abort.
7. **On approval** — set `Status: APPROVED`, finalize the Recommendation. Offer to record the chosen
   decision as an ADR in `emkeel-governance/adr/`. Remind them to add `Strategy: <topic>` to feature
   specs (the `check_strategy_link` gate enforces it).

Never skip the human gate. Never cite a source you didn't open.
