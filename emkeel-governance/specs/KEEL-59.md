# KEEL-59 — New-project fixes (main branch, owner/repo) + README Windows install

## Context
A real Windows new-repo test surfaced: (1) `git init` created `master`, mismatching branch
protection (`main`) and mis-firing finish-adopt; (2) a bare repo name (no owner) broke the links
and the gh API calls (404); (3) the README's Windows install said `pipx install emkeel`, which
fails on PATH — what actually worked was `py -m pipx install emkeel` + a new terminal.

## Plan
- `src/emkeel/wizard.py` — new project: force the default branch to `main` (symbolic-ref, any git).
  Validate the GitHub repo as `owner/repo` (re-ask if a bare name). `tests/test_wizard.py`.
- `README.md` — Windows install uses `py -m pipx install emkeel`; add Windows notes (winget for
  Python, "Add to PATH", new-terminal / restart-VS-Code PATH gotcha, `py -m pipx`). Bump 0.1.45.

## Acceptance Criteria
- A new project's first branch is `main` (not `master`).
- The wizard rejects a repo without an owner and re-asks for `owner/repo`.
- The README Windows install matches what works (`py -m pipx install emkeel` + new terminal).

## Anti-regression
- Tests: run_setup(new) → branch is `main`; main() re-asks on a bare repo name until owner/repo.
