# Emkeel

Framework de gobernanza SDLC — **adopt-and-thin**. La quilla sobre la que se
construyen proyectos paso a paso: trazables, sin regresiones, con la IA como
ejecutor bajo gates deterministas.

## Principio central

> **"done" = hecho computado** (el artefacto existe + pasa un check determinista),
> nunca un flag auto-atestado. El enforcement vive **server-side** (CI + branch
> protection), fuera del alcance del agente. Pocos gates duros + un gate humano.

## Cómo está organizado (separación estructural, día 1)

- `src/emkeel/` — **código distribuible** (lo único que se empaqueta).
- `emkeel-governance/` — **la única carpeta de artefactos** (ADR / specs / records). Un
  solo límite físico: `export-ignore` la excluye del paquete/tarball. Borra esa carpeta
  para separar artefactos del código; sálvala para respaldarlos. Nada más que separar.

Ver `AGENTS.md` (contrato del agente) y `docs/lifecycle.md` (la convención).

---
© 2026 EMillion Networking LTD — ver `LICENSE`.
