# 5. A generic governed-process engine for skills (state machine), distributable in emkeel

- Status: accepted
- Date: 2026-06-20
- Deciders: operator (EMillion Networking)
- Ticket: KEEL-89

## Context

emkeel's skills (`/strategy`, `/launch-satellite`, …) are **prose + an exit gate**: the steps are
described in markdown and a single gate checks the final artifact. Nothing stops an obligatory step from
being silently skipped — if the agent produces a plausible final artifact, it passes, even though (say)
the research step never really happened. "Skipping a step" is possible because the steps are advisory.

The 6-step **lifecycle** (em-development-framework `forge/tools/_state_machine.py`) does not have this
problem: it is a **state machine**. The engine REFUSES to advance into a step whose prerequisite isn't
met, state lives on disk as the single source of truth, and writes are lock-guarded. "Skipping a step"
doesn't exist — it's a mechanism, not a suggestion.

We want that same mechanism, **generic**, for any skill, and living in **emkeel** so every governed repo
inherits it via `pip install emkeel` — not in em-ecosystem, where it would be trapped and non-reusable.

## Decision

Add a **generic governed-process engine** to emkeel — `src/emkeel/process.py` (library) — that reuses the
proven lifecycle pattern:

- **A process = a `ProcessSchema`**: ordered `Step`s, each with optional required fields (the evidence
  it happened), an optional `prereq(state)` predicate, and an optional `validate(payload)` predicate.
  Declared as plain data by the adopting skill — the engine is **not hardcoded** to any skill.
- **Pure transitions + `evaluate_prereq`**: advancing into a step requires the previous step done AND the
  step's predicates — the engine raises `PrereqError` (refuses) otherwise. Skipping is impossible by
  construction.
- **State on disk = the truth**, written under an `fcntl.flock` lock (exclusive for writers, shared for
  readers, timeout → `LockTimeout`). Stdlib-only: **JSON, not PyYAML**, to keep emkeel zero-dependency.
- **Lib + thin CLI**: the engine is a library; the adopting skill exposes the thin CLI
  (`emkeel strategy advance <step> <topic>` / `status`).

**Skills become prereq-gated processes, not prose + an exit gate.** `/strategy` is the first adopter:
`scaffolded → researched → proposed → critiqued → checked → presented → approved`, each step
non-skippable. Notably, the `researched` step's gate **requires provenance** (≥1 verifiable external
source — a URL or repo `file:line` — OR an explicit `internal_only=true`), which **subsumes** the
separate research-provenance gate we were going to add; and `approved` requires a recorded human decision
(`approved_by`).

## Consequences

- **Obligatory steps can't be silently skipped** for any skill that adopts the engine — the refusal is in
  the engine, inherited by every governed repo via PyPI.
- **emkeel stays zero-dependency**: the engine uses `json` + `fcntl` from stdlib (the lifecycle's PyYAML
  is not pulled in). State files are `*.process.json` alongside the artifact, under `emkeel-governance/`
  (never shipped; gates that glob `*.md` ignore them).
- **The research-provenance gap is closed by the `researched` step**, not a one-off gate — fewer moving
  parts, one mechanism.
- **Adoption is incremental**: this ADR + engine + the `/strategy` schema + its `advance`/`status` CLI
  ship now; updating the `/strategy` prose in em-ecosystem to call `emkeel strategy advance <step>` is a
  follow-on (the prose is a thin driver over the tested engine).
- **Reuse, not reinvention**: the design mirrors `_state_machine.py` (schema state, pure `evaluate_prereq`,
  `_StateLock`, lib + CLI) — a known-good pattern, not a new one.
