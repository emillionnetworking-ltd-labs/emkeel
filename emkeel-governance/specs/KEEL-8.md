# KEEL-8 — Version pin in generated CI + bump to 0.1.0

## Context
Prep for public distribution. Today the generated CI installs `emkeel` UNPINNED, so a new
release would hit existing governed repos automatically and could break them. Pinning the
install spec means a user is unaffected by a new version until they opt in (SemVer contract).

## Plan
- `pyproject.toml` + `src/emkeel/__init__.py` — bump 0.0.1 → 0.1.0 (first distributable).
- `src/emkeel/init.py` — `--emkeel-source` defaults to a version-PINNED spec computed from
  `__version__` (`emkeel~=0.1.0`); 0.x pins the minor, >=1.0 pins the major.
- `tests/test_init.py` — assert the default is pinned, never a bare name.

## Acceptance Criteria
- emkeel version is `0.1.0` in pyproject and `__version__`.
- `emkeel init` (no `--emkeel-source`) generates CI with `pip install "emkeel~=0.1.0"`, not a bare `emkeel`.
- A custom `--emkeel-source` still overrides the default (e.g., a private git+token form).
- The pin is computed from `__version__`, so it tracks future bumps automatically.

## Anti-regression
- Tests cover: default source is pinned (`emkeel~=`) and never bare; custom source still flows through.
