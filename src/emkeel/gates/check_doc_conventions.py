"""Gate: governance docs use canonical English field names — across ALL artifacts — + bidirectional ADR
supersession (ADR-0008).

The lived bug was a LANGUAGE SPLIT: every emkeel gate parses a field by its English name (`check_strategy_
link` matches `^\\s*Strategy:`, `check_acceptance_criteria` matches the `Acceptance Criteria` heading), so a
doc that localizes the key (`Estado:`/`Estrategia:`/`## Criterios de Aceptación`) is read as "absent" — a
SILENT false negative. ADR-0008 made the keys a canonical-English contract.

This gate enforces ADR-0008's **language rule for EVERY governed artifact**, not just ADRs: it scans every
`*.md` under `emkeel-governance/` RECURSIVELY (adr, strategy, specs, records — and ANY future artifact type
or subdir, covered by default, so generalizing never leaves a per-type gap again) and FAILs on a known
localized field key or section heading where a canonical English one belongs. The ADR-only STRUCTURAL rules
(required fields, status enum, bidirectional supersession — a cross-file graph property) stay scoped to
`adr/`. Dormant when there's no governance dir / no docs. Shipped into every governed repo's CI by
`emkeel init`.
"""

from __future__ import annotations

import os
import re
import sys
import unicodedata
from pathlib import Path

GOVERNANCE_DIR = "emkeel-governance"
ADR_SUBDIR = "adr"

# ── Register 1: the canonical English vocabulary the machine parses (the single source of truth) ──
# Inline `Field:` keys that must stay canonical English. `Ticket:` is recommended, not required.
REQUIRED_ADR_FIELDS = ("status", "date", "deciders")
STATUS_ENUM = ("proposed", "accepted", "rejected", "deprecated", "superseded")   # MADR-grounded
CANONICAL_FIELDS = ("status", "date", "deciders", "ticket", "supersedes", "superseded-by", "strategy")
CANONICAL_HEADINGS = ("acceptance criteria", "alignment")

# A localized field key (normalized: lowercased, accents stripped) → the canonical English key to use.
# These are the localized forms of the canonical vocabulary above; using one is the silent-miss vector.
BANNED_FIELD_KEYS = {
    "estado": "Status", "fecha": "Date", "decisores": "Deciders", "deciser": "Deciders",
    "ticket de jira": "Ticket", "tique": "Ticket",
    "reemplaza": "Supersedes", "reemplazado-por": "Superseded-by", "reemplazado por": "Superseded-by",
    "sustituye": "Supersedes", "sustituido-por": "Superseded-by", "sustituido por": "Superseded-by",
    "estrategia": "Strategy",
}
# A localized section heading (normalized) → the canonical English heading.
BANNED_HEADINGS = {
    "criterios de aceptacion": "Acceptance Criteria", "criterio de aceptacion": "Acceptance Criteria",
    "alineacion": "Alignment", "alineamiento": "Alignment",
}

_FIELD_RE = re.compile(r"^\s*-?\s*([A-Za-z][\w -]*?)\s*:\s*(.*\S)?\s*$")
_HEADING_RE = re.compile(r"^#{1,6}\s+(.*\S)\s*$")


def _norm(s: str) -> str:
    """Lowercase + strip accents, so `Alineación` and `alineacion` compare equal."""
    nfkd = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c)).strip()


def _adr_num(name: str) -> int | None:
    m = re.match(r"^(\d+)", name)
    return int(m.group(1)) if m else None


def _refs(value: str) -> set[int]:
    """ADR numbers in a value — `ADR-0007` / `ADR-7` / a bare `0007` → {7}. A bare small number is
    ignored (a ref needs the `ADR` prefix or a 4-digit zero-padded form)."""
    out: set[int] = set()
    for m in re.finditer(r"ADR[-\s]?0*(\d+)|(?<!\d)(\d{4})(?!\d)", value or "", flags=re.I):
        out.add(int(m.group(1) or m.group(2)))
    return out


def language_problems(text: str, name: str) -> list[str]:
    """The UNIVERSAL register-1 rule applied to ONE artifact: a localized field key or section heading
    where a canonical English one belongs → a problem. Runs on every governed artifact type."""
    problems: list[str] = []
    seen_keys: set[str] = set()
    seen_headings: set[str] = set()
    for line in text.splitlines():
        fm = _FIELD_RE.match(line)
        if fm:
            key = _norm(fm.group(1))
            if key in BANNED_FIELD_KEYS and key not in seen_keys:
                seen_keys.add(key)
                problems.append(f"{name}: localized field key '{fm.group(1).strip()}:' — use the canonical "
                                f"English field name '{BANNED_FIELD_KEYS[key]}:' (ADR-0008).")
        hm = _HEADING_RE.match(line)
        if hm:
            h = _norm(hm.group(1))
            if h in BANNED_HEADINGS and h not in seen_headings:
                seen_headings.add(h)
                problems.append(f"{name}: localized section heading '{hm.group(1).strip()}' — use the "
                                f"canonical English heading '{BANNED_HEADINGS[h]}' (ADR-0008).")
    return problems


def _parse_adr_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        m = _FIELD_RE.match(line)
        if not m:
            continue
        key = m.group(1).strip().lower()
        if key in CANONICAL_FIELDS and key not in fields:
            fields[key] = (m.group(2) or "").strip()
    return fields


def adr_structural_problems(adr_dir: Path) -> list[str]:
    """ADR-only structural rules: required fields, the status enum, and bidirectional supersession."""
    problems: list[str] = []
    docs: dict[int, dict] = {}
    for p in sorted(adr_dir.glob("*.md")):
        num = _adr_num(p.name)
        if num is None:
            continue
        f = _parse_adr_fields(p.read_text(encoding="utf-8", errors="replace"))
        for req in REQUIRED_ADR_FIELDS:
            if req not in f:
                problems.append(f"{p.name}: missing required field '{req[:1].upper()}{req[1:]}:'.")
        st = f.get("status", "").lower()
        if st and st not in STATUS_ENUM:
            problems.append(f"{p.name}: Status '{st}' is not in the enum {{{', '.join(STATUS_ENUM)}}}.")
        docs[num] = {"name": p.name, "status": st,
                     "supersedes": _refs(f.get("supersedes", "")),
                     "superseded_by": _refs(f.get("superseded-by", ""))}

    for num, d in docs.items():
        for y in sorted(d["supersedes"]):
            if y not in docs:
                problems.append(f"{d['name']}: Supersedes ADR-{y:04d}, which does not exist.")
                continue
            yd = docs[y]
            if num not in yd["superseded_by"]:
                problems.append(f"{d['name']}: Supersedes ADR-{y:04d} but ADR-{y:04d} ({yd['name']}) lacks "
                                f"'Superseded-by: ADR-{num:04d}' (one-way link).")
            if yd["status"] != "superseded":
                problems.append(f"{yd['name']}: superseded by ADR-{num:04d} but its Status is "
                                f"'{yd['status'] or '(none)'}', not 'superseded'.")
        for x in sorted(d["superseded_by"]):
            if x not in docs:
                problems.append(f"{d['name']}: Superseded-by ADR-{x:04d}, which does not exist.")
                continue
            if num not in docs[x]["supersedes"]:
                problems.append(f"{d['name']}: Superseded-by ADR-{x:04d} but ADR-{x:04d} ({docs[x]['name']}) "
                                f"lacks 'Supersedes: ADR-{num:04d}' (one-way link).")
    return problems


def lint(gov_dir: Path) -> list[str]:
    """All convention problems across every governed artifact (empty list = clean)."""
    problems: list[str] = []
    # UNIVERSAL language rule — every *.md anywhere under the governance dir (future types covered).
    for p in sorted(gov_dir.rglob("*.md")):
        rel = p.relative_to(gov_dir).as_posix()
        problems += language_problems(p.read_text(encoding="utf-8", errors="replace"), rel)
    # ADR-only structural rules.
    adr_dir = gov_dir / ADR_SUBDIR
    if adr_dir.is_dir():
        problems += adr_structural_problems(adr_dir)
    return problems


def main() -> int:
    repo = Path(os.environ.get("EMKEEL_REPO_DIR", "."))
    gov_dir = repo / GOVERNANCE_DIR
    docs = sorted(gov_dir.rglob("*.md")) if gov_dir.is_dir() else []
    if not docs:
        print(f"OK: no governed docs under {GOVERNANCE_DIR}/ — doc-conventions check N/A (dormant).")
        return 0
    problems = lint(gov_dir)
    if problems:
        for pr in problems:
            print(f"::error::{pr}", file=sys.stderr)
        print(f"FAIL: {len(problems)} governance-doc convention problem(s) — fix the localized field "
              "name(s)/heading(s) or supersession backlink(s) above (ADR-0008).", file=sys.stderr)
        return 1
    print(f"OK: {len(docs)} governed doc(s) use canonical English field names; ADRs in enum; "
          "supersession bidirectional.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
