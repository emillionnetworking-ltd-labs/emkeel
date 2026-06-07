# KEEL-11 — PyPI release workflow + installer default to PyPI

## Context
Model A chosen: repo stays PRIVATE (governance hidden), distribute the PACKAGE on PyPI
(public). This adds the release pipeline and reverts the installer default to the PyPI
pin (KEEL-10's public-git default is superseded — the repo is private again).

## Plan
- `.github/workflows/release.yml` — on a GitHub Release (or manual dispatch), build
  wheel+sdist and publish to PyPI via **Trusted Publishing (OIDC, no token)**.
- `src/emkeel/init.py` — `_default_source()` returns `emkeel~=0.{minor}.0` (PyPI pin),
  not the git URL. Private fork still overridable via `--emkeel-source`.
- `tests/test_init.py` + `docs/install.md` — assert/document the PyPI default.

## Acceptance Criteria
- `emkeel init` (no `--emkeel-source`) generates CI with `pip install "emkeel~=0.1.0"`.
- `release.yml` builds and publishes via Trusted Publishing (`id-token: write`, the
  `pypa/gh-action-pypi-publish` action) — no PyPI token stored in the repo.
- A custom `--emkeel-source` (private git+token) still overrides.
- The release workflow ships only in emkeel's own repo (NOT scaffolded into governed repos).

## Anti-regression
- Tests cover: default source is the PyPI pin (`emkeel~=`), never bare; custom source overrides.
