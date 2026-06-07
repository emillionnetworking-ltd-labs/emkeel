# Emkeel

SDLC governance framework — **adopt-and-thin**. The keel projects are built on, step by
step: traceable, regression-free, with AI as an executor under deterministic gates.

## Core principle

> **"done" = a computed fact** (the artifact exists + passes a deterministic check),
> never a self-attested flag. Enforcement lives **server-side** (CI + branch protection),
> out of the agent's reach. A few hard gates + one human gate.

## Layout (structural separation, day 1)

- `src/emkeel/` — **distributable code** (the only thing packaged).
- `emkeel-governance/` — **the single artifacts folder** (ADR / specs / records). One
  physical boundary: `export-ignore`, never shipped. Delete it for code-only; save it to back it up.

See `AGENTS.md` (the agent contract) and `docs/lifecycle.md` (the convention).

---
Licensed under **Apache-2.0** — © 2026 EMillion Networking LTD (see `LICENSE` / `NOTICE`).
