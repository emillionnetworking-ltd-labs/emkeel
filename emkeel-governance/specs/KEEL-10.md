# KEEL-10 — Installer default to public git source

## Context
Emkeel is now public + tagged `v0.1.0`, so a governed repo can install it token-less from
the public repo. The installer's default `--emkeel-source` should reflect that (the prior
default `emkeel~=…` won't resolve until PyPI exists).

## Plan
- `src/emkeel/init.py` — `_default_source()` returns `git+<public-repo>@v{__version__}`
  (token-less, tag-pinned, tracks version bumps).
- `tests/test_init.py` — assert the default is the public git URL pinned to `@v{version}`.
- `docs/install.md` — document the public-git default; PyPI/private-fork as alternatives.

## Acceptance Criteria
- `emkeel init` (no `--emkeel-source`) generates CI installing from
  `git+https://github.com/.../emkeel.git@v0.1.0` — public, no token.
- The pin tracks `__version__` (`@v{version}`), so a release/tag bump updates the default.
- A custom `--emkeel-source` (PyPI spec or private git+token) still overrides.
- The default needs no secret (no `EMKEEL_INSTALL_TOKEN`).

## Anti-regression
- Tests cover: default is public git + tag-pinned (`@v{version}`), never bare; custom
  source still flows through; checklist mentions the token only for private sources.
