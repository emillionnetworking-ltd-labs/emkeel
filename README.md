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
- `governance/` — **artefactos** (ADR / specs / records). `export-ignore`: **nunca**
  entra al paquete ni al tarball. Si hay que distribuir, no hay que separar nada.

Ver `AGENTS.md` (contrato del agente) y `docs/lifecycle.md` (la convención).

---
© 2026 EMillion Networking LTD — ver `LICENSE`.
