# 13. The critique step requires a multi-lens adversarial panel, not a one-liner

- Status: accepted
- Date: 2026-06-26
- Deciders: operator (EMillion Networking)
- Ticket: KEEL-118

## Context

ADR-0005 made `/strategy` a non-skippable governed process; KEEL-114 added the reality bar (`validated`). But
the `critiqued` step still only required a string `critique`. An agent could record a single line — "looks
fine" — and pass. The depth of the adversarial pass was left to chance, so the substance verification that is
supposed to catch a weak strategy was effectively optional. This is the same shape as the holes KEEL-114
(reality) and KEEL-115 (retiro) closed: the process proved a step *happened*, not that it had *substance*.

A gate cannot judge whether a critique is *good* (subjective). But — exactly as the reality gate requires the
outcome evidence to *exist and be structured* without judging it — it can require that a real multi-angle
critique was recorded: several distinct lenses, each with a finding, plus a completeness critic. Depth
becomes a recorded, enforceable fact, while the human still judges quality at approval.

## Decision

Make `critiqued` carry a structured **adversarial panel**, with a cheap path for trivial strategies:

- **Engine baseline**: `critiqued` requires ≥1 named lens (`lens_<angle>=<finding>` — one field per lens, so
  a finding may contain commas/colons safely) AND a `completeness` critic (`completeness=<what's missing>`).
  A one-line `critique` no longer advances the step.
- **Gate floor**: `check_strategy_process` requires **≥3 distinct lenses** for a non-trivial strategy,
  thresholded by the doc's declared `Impact:` (`low` → ≥1; absent / `medium` / `high` → ≥3). `Impact`
  defaults to `high` when absent, so omitting it never dodges the panel — only a conscious `Impact: low`
  lowers the bar.
- **Author-named lenses, not a fixed set**: the gate counts *distinct* lenses and never judges which angles
  apply — a content-blind, distributable rule. The `/strategy` skill RECOMMENDS a default panel
  (discovery/SEO, professional completeness, calibration to the real case, legal/compliance) and runs one
  subagent per lens, but the author picks the angles that fit the topic.
- **Back-compat for free**: a committed `critiqued` with no lenses (the old one-line `critique`) is
  grandfathered. The engine makes a lens-less `critiqued` unreachable under the new schema, so "no lenses"
  can only mean a state recorded before this change — no schema version stamp is needed (unlike KEEL-114).

## Consequences

- **Depth is enforced, not hoped for**: a strategy can no longer pass critique with a single line; the gate
  requires a genuine multi-angle pass + a completeness check, exported to every governed repo.
- **Cheap stays cheap**: a trivial strategy declares `Impact: low` and passes with one lens + completeness —
  the bar scales with stated impact, not doc size (a short high-stakes decision still gets the full panel).
- **Honest limit**: like every emkeel gate, it checks structure (N distinct recorded lenses), not quality —
  the human judges substance at approval. It raises the cost from one line to N recorded angles.
- **Same pattern as reality/retiro**: fix the tool (the governed process), not the symptom (a weak critique
  caught late or never).
