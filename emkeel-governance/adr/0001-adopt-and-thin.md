# 1. Emkeel adopta gobernanza adopt-and-thin

- Estado: aceptado
- Fecha: 2026-06-06
- Deciders: operador (EMillion Networking)

## Contexto

El framework v1 (`em-development-framework`, engine LangGraph bespoke) se volvió
insostenible para un solo dev: cada escalado se desorganizaba (footgun de `--work-impl=stub`,
replan W69, scope drift 4×). Un research de mercado (deep-research, 2026-06-06, verificado
adversarialmente) confirmó el consenso: para un equipo solo/diminuto se **componen
herramientas off-the-shelf**, no se construye un framework bespoke (el anti-patrón).

## Decisión

Emkeel compone: **GitHub** (branch protection + Actions CI), **Jira** (workflow),
**Conventional Commits**, **ADRs markdown**, y **Claude Code** (skills/subagents/hooks +
AGENTS.md). El único código propio es una capa fina: **gates deterministas** + el patrón
**Plan-Execute-Verify** + el pegamento **ADR↔sesión** (trazabilidad spec a largo plazo,
brecha no resuelta del mercado). `"done"` = hecho computado; enforcement server-side;
pocos gates duros + gate humano.

## Consecuencias

- v1 **congelado** (cantera read-only). W70/W71 **cancelados**.
- **Separación estructural día 1**: `src/` (distribuible) vs `emkeel-governance/` (la única
  carpeta de artefactos, `export-ignore`). Un solo límite físico. Nunca más un cutover.
- **Anti-regresión**: test-on-fix + CI corre la suite completa en cada PR.

## Alternativas consideradas

- Seguir parchando v1 → rechazado (arrastra errores).
- Reconstruir otro engine bespoke → rechazado (*second-system trap*).

## Referencias

- Research de mercado (deep-research, 2026-06-06).
- Memoria del operador: `project-emkeel-v2-pivot`.
