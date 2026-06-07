# 2. Emkeel is licensed Apache-2.0 (free / open-source)

- Status: accepted
- Date: 2026-06-07
- Deciders: operator (EMillion Networking)

## Context
Emkeel started under a provisional proprietary license. The operator decided to
distribute it **free / open-source first** (adoption now; monetize later via open-core).
A permissive OSS license also removes the private-package friction: once on PyPI,
`pip install emkeel` works for anyone — no install token.

## Decision
License Emkeel under **Apache-2.0**. Chosen over MIT for its explicit **patent grant**
(safer for a tool that may be commercialized later). The repos Emkeel *governs* stay
private — only the framework itself is public.

## Consequences
- `LICENSE` replaced (proprietary → Apache-2.0 verbatim) + `NOTICE` added.
- `pyproject.toml` declares Apache-2.0.
- Distribution path opens: PyPI (public), `pip install emkeel`, no token.
- Re-licensable by the copyright holder; contributions covered by Apache-2.0 §5.

## Alternatives considered
- **MIT** — simpler, but no explicit patent grant.
- **Stay proprietary** — blocks free distribution and keeps the install-token friction.
