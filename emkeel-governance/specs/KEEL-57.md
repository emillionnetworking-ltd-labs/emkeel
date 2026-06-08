# KEEL-57 — AGENTS.md routes Emkeel operations through `emkeel onboard`

## Context
When asked a bare `emkeel <cmd>`, an AI improvises instead of following the playbook (it hadn't been
told to). The agent contract `AGENTS.md` (read by coding agents at session start) is the right place
to route them: any Emkeel task → `emkeel onboard` first. Best-effort (gates remain the hard guarantee).

## Plan
- `src/emkeel/init.py` — the generated `AGENTS.md` gains a "Managing Emkeel itself" rule: for any
  Emkeel task, run `emkeel onboard` first and follow it (single entry point; don't improvise
  subcommands). `tests/test_init.py`. Bump 0.1.42.

## Acceptance Criteria
- The generated AGENTS.md instructs the agent to route Emkeel operations through `emkeel onboard`.

## Anti-regression
- Test asserts the generated AGENTS.md mentions `emkeel onboard` as the single entry point.
