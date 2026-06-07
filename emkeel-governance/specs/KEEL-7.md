# KEEL-7 — Configurable install-source (`--emkeel-source`)

## Context
Governing another repo was blocked: the generated CI hardcoded `pip install emkeel`,
which fails for a PRIVATE package. `emkeel init` gains `--emkeel-source` so the CI can
install emkeel from a private git source via a token secret. Unblocks the real trial.

## Plan
- `src/emkeel/init.py` — add `Config.emkeel_source` + `--emkeel-source` flag; thread it
  into the generated `emkeel-ci.yml` / `jira-transition.yml` install step and `emkeel.toml`;
  checklist mentions `EMKEEL_INSTALL_TOKEN` only for a private (token) source.
- `tests/test_init.py` — source flows into both workflows + toml; default is `emkeel`;
  checklist is conditional.
- `docs/install.md` — document `--emkeel-source` and the private git+token form.

## Acceptance Criteria
- `--emkeel-source SRC` makes the generated CI run `pip install "SRC"` (both workflows).
- The chosen source is recorded in `emkeel.toml` under `[emkeel] source`.
- Default source is `emkeel` (the PyPI name, for when published).
- The connection checklist mentions `EMKEEL_INSTALL_TOKEN` only when the source uses it.
- No secret value is written to any file.

## Anti-regression
- Tests cover: custom source in both workflows + toml, default source, and the
  conditional checklist (token mentioned only for a private source).
