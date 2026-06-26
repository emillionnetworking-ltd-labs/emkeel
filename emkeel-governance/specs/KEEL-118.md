# KEEL-118 — critiqued requires a multi-lens adversarial panel + a completeness critic

Strategy: none

## Context
`/strategy`'s `critiqued` step only required a string `critique` — an agent could record a one-line critique
and pass; depth was left to chance. The substance verification was optional. Mirror of the retiro and
reality-gate KEELs: fix the tool, not the symptom. This makes the multi-lens adversarial pass part of the
governed process — recorded evidence the gate enforces — while staying cheap for trivial strategies.
Standalone, decided in ADR-0013 — hence `Strategy: none`.

## Plan
1. **`critiqued` step** → `validate=_critique_panel` (drop the bare `requires=("critique",)`): the engine
   BASELINE refuses anything without ≥1 named lens (`lens_<angle>=<finding>`, one field per lens so a finding
   may contain commas/colons) AND a `completeness` critic ("what dimension is missing").
2. **Gate `check_strategy_process`** raises the floor to **≥3 distinct lenses** for non-trivial strategies,
   thresholded by the doc's `Impact:` (low → ≥1; absent/medium/high → ≥3). `doc_impact(text)` defaults to
   `high` (non-evasible). A legacy `critiqued` with no lenses is GRANDFATHERED — the engine makes a lens-less
   critique unreachable under the new schema, so "no lenses" can only be a pre-change state (no version stamp
   needed).
3. **`Impact: low|medium|high`** line added to the scaffold; `FULL_PANEL_LENSES = 3`.
4. **`/strategy` skill** step 4 rewritten as a subagent PANEL (one per lens) + a completeness critic,
   recommending the default angles (discovery/SEO, professional completeness, calibration to the real case,
   legal/compliance) and noting the `Impact: low` cheap path. Self-installed `SKILL.md` regenerated.
5. **ADR-0013**. Integration test (real engine + gate). Bump 0.1.101.

## Acceptance Criteria
1. The engine REFUSES `critiqued` with only a one-line `critique` (no lenses) and REFUSES it without a
   `completeness` critic; it accepts ≥1 lens + completeness (baseline).
2. The gate FAILS a non-trivial strategy whose `critiqued` has < 3 distinct lenses; PASSES with ≥3; PASSES
   with 1 lens when the doc declares `Impact: low`. `Impact:` absent or unrecognized → high (≥3).
3. A legacy `critiqued` (one-line `critique`, no lenses) is grandfathered → PASS (not retro-broken).
4. The lenses are author-named (the gate counts distinct `lens_*`, never judges which angles) — domain
   agnostic and distributable; the skill recommends defaults.
5. `doc_impact` defaults to high. Real-engine+gate integration test covers 3-lens→PASS, 1-lens-high→FAIL,
   1-lens-low→PASS. Bump 0.1.101; all tests pass.
