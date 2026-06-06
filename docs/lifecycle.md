# Lifecycle (lean)

```
rama  →  artefactos  →  PR  →  gates  →  merge
```

| Paso | Artefacto | Gate (server-side, no falsificable) |
|---|---|---|
| plan | `emkeel-governance/specs/<KEY>.md` (solo features) | CI: existe + valida |
| develop | código + tests | CI: lint + types + **suite completa** verde |
| verify | (CI) + tu review | required check + required approval |
| decisión | `emkeel-governance/adr/NNNN-*.md` | CI: ADR presente si toca zona marcada |
| merge | — | branch protection: CI verde + approval + ticket ligado |

## Por qué funciona

- **"done" = el check pasa**, no un flag que el agente escribe. (Con LangGraph y sin
  LangGraph el agente se saltaba reglas porque eran auto-atestadas; el orquestador
  nunca fue la variable — el locus de autoridad sí.)
- La **suite de tests es la memoria durable** anti-regresión: el agente olvida entre
  sesiones, la suite no. Re-romper algo viejo = CI rojo = bloqueado.
- Lo no-mecanizable lo cubre **tu gate humano** (aprobar el PR), no más prosa.
