# KEEL-4 — Review-assist helper + playbook

## Context
Formalizes the AI-assisted review demonstrated on KEEL-3: given a ticket's Acceptance
Criteria + the PR diff, produce a per-criterion verdict in plain language. Advisory —
the human approves, the AI never merges. NOT a deterministic gate.

## Plan
- `src/emkeel/review.py` — `extract_criteria()` + `render_review_template()` + CLI
  `python -m emkeel.review <KEY>` (deterministic: gathers and structures the inputs).
- `tests/test_review.py` — tests incl. `main()` end-to-end (KEEL-2 lesson).
- `docs/review-assist.md` — the playbook (how the reviewer fills the verdict; ratchet).

## Acceptance Criteria
- `extract_criteria` returns the bullet items under the "Acceptance Criteria" heading, in order.
- `python -m emkeel.review KEEL-4` prints a template with one section per criterion.
- The helper is advisory only: it adds NO CI gate and cannot block a merge.
- This PR's spec carries Acceptance Criteria, so KEEL-3's gate passes.

## Anti-regression
- Tests cover: criteria extraction (present / absent / stops at next heading),
  template rendering (with and without criteria), and `main()` exit codes (present / missing / no-args).
