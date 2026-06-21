# AGENTS.md — Agent contract (Emkeel)

You are an **executor under deterministic gates**. The rules that matter do NOT live in
this file (it is best-effort and can be ignored); they live in **CI + branch protection**,
which you cannot bypass. If something can be skipped, it is not a gate — it is a suggestion.

## The loop

1. One branch per ticket: `feat/<KEY-123>-slug` for features; `fix/`, `chore/`, `docs/` otherwise.
2. Produce the change's artifacts: a spec (if a feature) → code → tests.
3. **Every bug fix starts with a failing test** that reproduces it (a permanent regression guard).
4. Open a PR. Merge requires: **CI green + human approval + a linked ticket**.
5. Architectural decision? An ADR in `emkeel-governance/adr/`.

## Hard rules (enforced by CI, not this file)

- The **full test suite** runs on every PR. Re-break something old → CI red → no merge.
- Commits: **Conventional Commits** with the ticket KEY.
- No `--no-verify`. No marking "done" without the check computing it.

## Separation (structural, non-negotiable)

- `src/emkeel/` = distributable code.
- `emkeel-governance/` = the ONLY artifacts folder (ADR/specs/records). **Never** shipped
  (`export-ignore`). It is the single physical boundary: delete it = clean code.

> Note: Claude Code reads `CLAUDE.md` (a symlink → this file).
