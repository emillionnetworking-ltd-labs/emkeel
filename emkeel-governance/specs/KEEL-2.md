# KEEL-2 — Gate: plan-presence para features

## Contexto
Primer ticket dogfood: el primer cambio real que recorre el loop de Emkeel
(rama → PR → gates CI → merge). Añade el segundo gate determinista.

## Plan
- `src/emkeel/gates/check_plan_present.py` — el gate: una rama `feat/` exige
  `emkeel-governance/specs/<KEY>.md`; otros tipos no.
- `tests/test_check_plan_present.py` — su test (test-on-fix desde el día 1).
- `.github/workflows/ci.yml` — nuevo step que corre el gate en PRs.

## Verificación
- `pytest` verde (incluye el nuevo test).
- Auto-validación: este PR es `feat/KEEL-2-...`, así que el gate corre sobre sí mismo
  y exige este mismo spec → debe pasar porque el archivo existe.

## Anti-regresión
- El test cubre: feature requiere spec, no-feature no, y detección de spec presente.
