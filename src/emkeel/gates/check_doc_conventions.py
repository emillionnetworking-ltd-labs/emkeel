"""Gate: governance docs use canonical English fields + bidirectional ADR supersession (ADR-0008).

The lived bug was a LANGUAGE SPLIT: every emkeel gate parses inline `Field:` lines by an English name
(`check_strategy_link.py` matches `^\\s*Strategy:`), so a doc that localizes the key (`Estado:` vs
`Status:`) is read as "field absent" — a SILENT false negative. This gate converts silent-miss → loud-fail:
it REQUIRES the canonical English fields, bans known localized keys, checks Status against the MADR enum,
and enforces that ADR supersession is BIDIRECTIONAL (a graph property across files).

Scans ALL ADRs under `emkeel-governance/adr/` each run (like `check_strategy_quality` lints every strategy
doc) — a scoped diff scan would let editing X silently break Y's backlink. Dormant when there's no `adr/`
or it's empty. Shipped into every governed repo's CI by `emkeel init`.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ADR_DIR = "emkeel-governance/adr"

# Register 1 (field NAMES the machine parses): canonical English, fixed vocabulary.
REQUIRED_FIELDS = ("status", "date", "deciders")        # `Ticket:` is recommended, not required
STATUS_ENUM = ("proposed", "accepted", "rejected", "deprecated", "superseded")   # MADR-grounded
CANONICAL_FIELDS = ("status", "date", "deciders", "ticket", "supersedes", "superseded-by")
# A localized field key → the canonical English key to use instead. A doc using one of these FAILS.
BANNED_KEYS = {
    "estado": "Status", "fecha": "Date", "decisores": "Deciders", "deciser": "Deciders",
    "reemplaza": "Supersedes", "reemplazado-por": "Superseded-by", "reemplazado por": "Superseded-by",
    "sustituye": "Supersedes", "sustituido-por": "Superseded-by",
}

_FIELD_RE = re.compile(r"^\s*-?\s*([A-Za-z][\w -]*?)\s*:\s*(.*\S)?\s*$")


def _adr_num(name: str) -> int | None:
    m = re.match(r"^(\d+)", name)
    return int(m.group(1)) if m else None


def _refs(value: str) -> set[int]:
    """ADR numbers referenced in a field value — `ADR-0007` / `ADR-7` / a bare `0007` → {7}. A bare small
    number (`3 reasons`) is ignored: a ref needs the `ADR` prefix or 4-digit zero-padded form."""
    out: set[int] = set()
    for m in re.finditer(r"ADR[-\s]?0*(\d+)|(?<!\d)(\d{4})(?!\d)", value or "", flags=re.I):
        out.add(int(m.group(1) or m.group(2)))
    return out


def parse_doc(text: str) -> dict:
    """First-occurrence map of canonical fields + any localized keys seen (the banned ones)."""
    fields: dict[str, str] = {}
    banned: list[str] = []
    for line in text.splitlines():
        m = _FIELD_RE.match(line)
        if not m:
            continue
        key = m.group(1).strip().lower()
        val = (m.group(2) or "").strip()
        if key in BANNED_KEYS and key not in banned:
            banned.append(key)
        if key in CANONICAL_FIELDS and key not in fields:
            fields[key] = val
    return {"fields": fields, "banned": banned}


def lint(adr_dir: Path) -> list[str]:
    """Every convention problem across all ADRs (empty list = clean)."""
    problems: list[str] = []
    docs: dict[int, dict] = {}
    for p in sorted(adr_dir.glob("*.md")):
        num = _adr_num(p.name)
        if num is None:
            continue                                    # not a numbered ADR (e.g. a README) — skip
        parsed = parse_doc(p.read_text(encoding="utf-8", errors="replace"))
        f = parsed["fields"]
        for b in parsed["banned"]:
            problems.append(f"{p.name}: localized field key '{b[:1].upper()}{b[1:]}:' — use the canonical "
                            f"English field name '{BANNED_KEYS[b]}:'.")
        for req in REQUIRED_FIELDS:
            if req not in f:
                problems.append(f"{p.name}: missing required field '{req[:1].upper()}{req[1:]}:'.")
        st = f.get("status", "").lower()
        if st and st not in STATUS_ENUM:
            problems.append(f"{p.name}: Status '{st}' is not in the enum "
                            f"{{{', '.join(STATUS_ENUM)}}}.")
        docs[num] = {"name": p.name, "status": st,
                     "supersedes": _refs(f.get("supersedes", "")),
                     "superseded_by": _refs(f.get("superseded-by", ""))}

    # Bidirectional supersession — `Supersedes: ADR-Y` in X ⇔ `Superseded-by: ADR-X` in Y, Y is `superseded`.
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


def main() -> int:
    repo = Path(os.environ.get("EMKEEL_REPO_DIR", "."))
    adr_dir = repo / ADR_DIR
    adrs = sorted(adr_dir.glob("*.md")) if adr_dir.is_dir() else []
    if not adrs:
        print(f"OK: no ADRs under {ADR_DIR}/ — doc-conventions check N/A (dormant).")
        return 0
    problems = lint(adr_dir)
    if problems:
        for pr in problems:
            print(f"::error::{pr}", file=sys.stderr)
        print(f"FAIL: {len(problems)} governance-doc convention problem(s) — fix the field name(s) / "
              "supersession backlink(s) above.", file=sys.stderr)
        return 1
    print(f"OK: {len(adrs)} ADR(s) use canonical English fields; Status in enum; supersession bidirectional.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
