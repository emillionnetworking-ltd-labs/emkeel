# KEEL-64 — Config maintenance UX: honest `emkeel update` + `emkeel set` + preserve source

## Context
`emkeel update` reported "create" for every file on every run (force-overwrite) even when nothing
changed → confusing ("algo que no se cambia"). And there was no clean way to change a config value
(e.g. project_key SCRUM→ECO) other than hand-editing emkeel.toml (which the operator rejects).

## Plan
- `src/emkeel/update.py` — `main()` is content-aware: created/updated/appended/unchanged; a no-op
  prints "already current". `load_cfg` preserves a custom `[emkeel] source` (don't clobber fork pins).
- `src/emkeel/setcfg.py` — `emkeel set <jira-project|jira-url|github-repo> <value>` regenerates
  emkeel.toml with the one field changed (source + governance preserved).
- `src/emkeel/cli.py` — wire `set`; update usage/docstring. Tests. Bump 0.1.50.

## Acceptance Criteria
- A second `emkeel update` with no changes prints "already current"; a real change lists only what changed.
- `emkeel set jira-project ECO` updates emkeel.toml (project_key=ECO), preserves a custom source, reports old→new.
- load_cfg preserves a custom emkeel_source.

## Anti-regression
- Tests: update no-op vs only-changed; load_cfg preserves source; set changes/preserves-source/no-op/rejects-unknown.
