# KEEL-72 — emkeel strategy: deterministic scaffold (new) + lint (check)

## Context
Layer 2 core, mechanized + tested (the reliability lives in code; the skill is a thin prose shell).
The lint is the anti-hallucination "computed fact": an option with no source fails.

## Plan
- `src/emkeel/strategy.py` — `new <topic>` scaffolds emkeel-governance/strategy/<topic>.md (Goal/
  Context/Options table/Recommendation/Non-goals/Decisions). `check [topic]` lints: required sections
  + >=2 filled options + EVERY option cites a Source. Pure `lint_strategy`/`_option_rows`. 
- `src/emkeel/cli.py` — wire `strategy`. `tests/test_strategy.py`. Bump 0.1.58.

## Acceptance Criteria
- `strategy new` scaffolds the structured doc (non-clobbering); `strategy check` exits 1 when an
  option lacks a source or a section is missing, 0 when grounded + complete; 0 when no docs.

## Anti-regression
- Tests: slug; skeleton sections; lint clean/missing-section/too-few-options/no-source; new scaffold+
  non-clobber; check fails-on-skeleton/passes-on-filled/no-docs.
