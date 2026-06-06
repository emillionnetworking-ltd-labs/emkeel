# AGENTS.md — Contrato del agente (Emkeel)

Eres un **ejecutor bajo gates deterministas**. Las reglas que importan NO viven en
este archivo (es best-effort y se puede ignorar); viven en **CI + branch protection**,
que no puedes saltarte. Si algo se puede saltar, no es un gate: es una sugerencia.

## Ciclo de un cambio

1. Una rama por ticket: `feature/<KEY-123>-slug`.
2. Produce los artefactos del cambio: plan (si es feature) → código → tests.
3. **Todo fix de bug empieza por un test que lo reproduce** (queda como regresión permanente).
4. Abre PR. El merge requiere: **CI verde + aprobación humana + ticket ligado**.
5. ¿Decisión arquitectónica? Un ADR en `governance/adr/`.

## Reglas duras (las enforza CI, no este archivo)

- La **suite completa** corre en cada PR. Si rompes algo viejo → CI rojo → no mergeas.
- Commits: **Conventional Commits** con la KEY del ticket.
- Prohibido `--no-verify`. Prohibido marcar "done" sin que el check lo compute.

## Separación (estructural, no negociable)

- `src/emkeel/` = código distribuible.
- `governance/` = artefactos (ADR/specs/records). **Nunca** se distribuye (`export-ignore`).

> Nota: Claude Code lee `CLAUDE.md` (symlink → este archivo).
