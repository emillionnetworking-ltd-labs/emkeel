"""Gate: un cambio de tipo *feature* debe traer su spec/plan.

Determinista, corre en CI. Si la rama es `feat/` (o `feature/`), exige que exista
`emkeel-governance/specs/<KEY>.md`. Otros tipos (chore/fix/docs) no lo requieren.
"done" = el spec existe, no un flag. Segundo eslabón de la trazabilidad ticket->spec.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from emkeel.gates.check_ticket_link import find_ticket_key

FEATURE_PREFIXES = ("feat/", "feature/")


def spec_required(branch: str) -> bool:
    """True si la rama denota una feature (y por tanto requiere spec)."""
    b = branch.strip().lower()
    return any(b.startswith(p) for p in FEATURE_PREFIXES)


def spec_path_for(key: str, specs_dir: Path) -> Path:
    return specs_dir / f"{key}.md"


def main() -> int:
    branch = os.environ.get("EMKEEL_BRANCH", "")
    specs_dir = Path(os.environ.get("EMKEEL_SPECS_DIR", "emkeel-governance/specs"))

    if not spec_required(branch):
        print(f"OK: rama '{branch}' no es feature; no requiere spec.")
        return 0

    key = find_ticket_key(branch)
    if not key:
        print(f"FALLO: rama feature '{branch}' sin key de ticket.", file=sys.stderr)
        return 1

    path = spec_path_for(key, specs_dir)
    if path.is_file():
        print(f"OK: spec presente para {key}: {path}")
        return 0

    print(
        f"FALLO: la feature {key} no tiene spec. Crea '{path}' antes de mergear.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
