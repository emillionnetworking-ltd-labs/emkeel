# 1. Emkeel adopts adopt-and-thin governance

- Status: accepted
- Date: 2026-06-06
- Deciders: operator (EMillion Networking)

## Context

The v1 framework (`em-development-framework`, a bespoke LangGraph engine) became
unsustainable for a solo dev: every scaling attempt got disorganized (the `--work-impl=stub`
footgun, the W69 replan, 4× scope drift). A market research pass (deep-research, 2026-06-06,
adversarially verified) confirmed the consensus: a solo/tiny team **composes off-the-shelf
tools**, it does not build a bespoke framework (the anti-pattern).

## Decision

Emkeel composes: **GitHub** (branch protection + Actions CI), **Jira** (workflow),
**Conventional Commits**, **markdown ADRs**, and **Claude Code** (skills/subagents/hooks +
AGENTS.md). The only custom code is a thin layer: **deterministic gates** + the
**Plan-Execute-Verify** pattern + the **ADR↔session** glue (long-term spec traceability — an
unsolved market gap). `"done"` = a computed fact; enforcement server-side; a few hard gates +
a human gate.

## Consequences

- v1 (`em-development-framework`) **frozen**: a read-only quarry, never patched/extended.
- **Structural separation day 1**: `src/` (distributable) vs `emkeel-governance/` (the single
  artifacts folder, `export-ignore`). One physical boundary. Never a cutover again.
- **Anti-regression**: test-on-fix + CI runs the full suite on every PR.

## Alternatives considered

- Keep patching v1 → rejected (drags errors forward).
- Rebuild another bespoke engine → rejected (*second-system trap*).

## References

- Market research (deep-research, 2026-06-06).
- Operator memory: `project-emkeel-v2-pivot`.
