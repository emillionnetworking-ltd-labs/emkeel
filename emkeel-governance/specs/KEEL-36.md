# KEEL-36 — Wizard: "existing" with no repo → inform + ask (not auto-switch)

## Context
The inverse cross-check: if the user picks "existing repo" but there's no git repo with
commits, the wizard auto-switched to "new project" and created it. If the user was in the
wrong folder, that silently makes an unwanted project. Make it consistent with the other
direction: inform and let them choose.

## Plan
- `src/emkeel/wizard.py` — when scenario is "existing" but `is_existing_repo` is false, print
  "no git repo here — right folder?" and offer **[1] Create a new project here** / **[c] Cancel**
  (instead of auto-switching). `tests/test_wizard.py`. Bump 0.1.20.

## Acceptance Criteria
- Answering "existing" in a folder with no git repo informs the user and asks (create-new or cancel).
- Choosing create-new proceeds as a new project (git init + scaffold).
- Cancelling changes nothing (no `.git`, no files).

## Anti-regression
- Tests cover: existing-in-no-repo asks then creates; and existing-in-no-repo cancel leaves nothing.
