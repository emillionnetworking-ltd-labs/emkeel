# KEEL-17 — emkeel CLI command + emkeel onboard (self-serve)

## Context
Two distribution gaps surfaced: (1) the `emkeel` console command didn't exist — the
README's `emkeel init` wouldn't run after `pip install` (only `python -m emkeel.init` did);
and (2) the onboarding playbook shipped only in the sdist, so a `pip install` user couldn't
access it. A new user shouldn't have to craft a prompt — they run one command.

## Plan
- `src/emkeel/cli.py` — dispatcher: `emkeel init | onboard | review`.
- `emkeel onboard` — prints a "paste to your AI agent" header + the bundled playbook
  (`src/emkeel/_docs/onboarding.md`, moved into the package so it ships in the wheel).
- `pyproject.toml` — `[project.scripts] emkeel = "emkeel.cli:main"`.
- `tests/test_cli.py`, README/install.md update, bump 0.1.4.

## Acceptance Criteria
- `emkeel` is a real command after install; `emkeel init`, `emkeel onboard`, `emkeel review` dispatch.
- `emkeel onboard` prints the onboarding playbook plus a "paste to your AI agent" header.
- The playbook ships **inside the wheel** (accessible after `pip install`, not only via the sdist).
- An unknown subcommand exits non-zero with usage; no args prints usage (exit 0).
- A new user starts with `pip install emkeel` + `emkeel onboard` — no prompt to craft, no local paths.

## Anti-regression
- Tests cover: usage (no args / unknown), `onboard` prints the playbook, `init`/`review` dispatch.
