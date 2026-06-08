# KEEL-43 — Wizard guides end-to-end (offers connect)

## Context
`emkeel setup` did the local scaffold and only *printed* the connect steps; the user had to
remember to run `emkeel connect` separately. The wizard should guide the whole way.

## Plan
- `src/emkeel/wizard.py` — after `setup` finishes, if `gh` is authenticated, offer to run
  `emkeel connect` right there (branch protection + secrets; new project: create+push too).
  Decline or no gh → the printed manual steps stand. `tests/test_wizard.py`. Bump 0.1.27.

## Acceptance Criteria
- After a successful `emkeel setup`, when gh is authed, the wizard offers to connect and runs
  `emkeel connect` if accepted; declining does nothing extra.
- When gh is not authenticated, no offer is made (the printed steps remain the guidance).

## Anti-regression
- Tests cover: connect offered + invoked when accepted; not invoked when declined; an autouse
  fixture isolates the other wizard tests from the offer.
