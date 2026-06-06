"""Gate: el cambio debe referenciar un ticket (p.ej. KEEL-12).

Determinista, corre en CI. Falla (exit 1) si no encuentra una key de ticket en el
nombre de la rama ni en el título del PR. Es el primer eslabón de trazabilidad
ticket->codigo. "done" = este check pasa, no un flag auto-atestado.
"""

from __future__ import annotations

import os
import re
import sys

# Key de ticket estilo Jira: 2+ mayúsculas, guion, número. Ej: KEEL-12, PROD-345.
KEY_RE = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b")


def find_ticket_key(*sources: str) -> str | None:
    """Devuelve la primera key de ticket encontrada en las fuentes dadas, o None."""
    for text in sources:
        match = KEY_RE.search(text or "")
        if match:
            return match.group(0)
    return None


def main() -> int:
    branch = os.environ.get("EMKEEL_BRANCH", "")
    pr_title = os.environ.get("EMKEEL_PR_TITLE", "")
    key = find_ticket_key(branch, pr_title)
    if key:
        print(f"OK: ticket '{key}' ligado (branch='{branch}' pr_title='{pr_title}').")
        return 0
    print(
        "FALLO: no se encontró una key de ticket (p.ej. KEEL-12) en la rama ni en el "
        f"título del PR. branch='{branch}' pr_title='{pr_title}'",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
