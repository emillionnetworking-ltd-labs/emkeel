"""emkeel strategy — scaffold + lint researched strategy artifacts.

  emkeel strategy new <topic>    scaffold emkeel-governance/strategy/<topic>.md (required structure)
  emkeel strategy check [topic]  lint strategy docs: required sections + EVERY option cites a Source

The `/strategy` skill fills the scaffold via grounded research; `check` is the deterministic gate
that catches an ungrounded/hallucinated doc (an option with no source → fail). "done" = check
passes, not prose. This module is pure + tested; the skill is a thin prose orchestrator on top.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

STRATEGY_DIR = "emkeel-governance/strategy"
REQUIRED_SECTIONS = ("Goal", "Context", "Options", "Recommendation")
_PLACEHOLDERS = {"", "-", "—", "tbd", "todo", "n/a", "<source>"}


def slug(topic: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", topic.strip().lower()).strip("-")
    return s or "strategy"


def skeleton(topic: str) -> str:
    return f"""# Strategy: {topic}

Status: DRAFT
Strategy: {slug(topic)}   <!-- feature specs reference this with a `Strategy: {slug(topic)}` line -->

## Goal
<one line: what this strategy decides for "{topic}">

## Context
<!-- grounded facts ONLY — cite file:line (repo) or a URL (market) for every claim -->
-

## Options
<!-- at least 2 real options; EVERY row MUST cite a Source (file:line or URL). `emkeel strategy check` enforces it. -->
| # | Option | Source | Pros | Cons | Risk |
|---|--------|--------|------|------|------|
| 1 |  |  |  |  |  |
| 2 |  |  |  |  |  |

## Recommendation
<which option + why — this is judgment; the human approves it at the gate>

## Non-goals
-

## Decisions
<!-- optional: link the chosen decision as an ADR, e.g. emkeel-governance/adr/007-<slug>.md -->
"""


def _split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _option_rows(text: str) -> list[dict]:
    """Parse the data rows of the table under '## Options' → [{option, source}]."""
    m = re.search(r"(?ims)^\s*#+\s*Options\b(.*?)(?=^\s*#+\s|\Z)", text)
    if not m:
        return []
    lines = [ln for ln in m.group(1).splitlines() if ln.strip().startswith("|")]
    if len(lines) < 2:
        return []
    header = [h.lower() for h in _split_row(lines[0])]

    def col(*names):
        for i, h in enumerate(header):
            if any(n in h for n in names):
                return i
        return None

    oi, si = col("option", "opci"), col("source", "fuente")
    rows = []
    for ln in lines[1:]:
        cells = _split_row(ln)
        if set("".join(cells)) <= set("-: "):          # |---| separator
            continue
        opt = cells[oi].strip() if oi is not None and oi < len(cells) else ""
        src = cells[si].strip() if si is not None and si < len(cells) else ""
        rows.append({"option": opt, "source": src})
    return rows


def lint_strategy(text: str) -> list[str]:
    """Deterministic problems with a strategy doc (empty list = OK). The anti-hallucination check."""
    problems = []
    for sec in REQUIRED_SECTIONS:
        if not re.search(rf"(?im)^\s*#+\s*{sec}\b", text):
            problems.append(f"missing section: ## {sec}")
    filled = [r for r in _option_rows(text) if r["option"]]
    if len(filled) < 2:
        problems.append("Options needs at least 2 filled options (research the alternatives)")
    for r in filled:
        if r["source"].strip().lower() in _PLACEHOLDERS:
            problems.append(f"option '{r['option'][:40]}' has no Source — cite a file:line or URL")
    return problems


def _do_new(topic: str, target: Path) -> int:
    if not topic:
        print("usage: emkeel strategy new <topic>", file=sys.stderr)
        return 2
    path = target / STRATEGY_DIR / f"{slug(topic)}.md"
    if path.exists():
        print(f"  {path} already exists — edit it (or `emkeel strategy check`).")
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(skeleton(topic), encoding="utf-8")
    print(f"emkeel strategy — scaffolded {path}\n"
          f"  Fill it with grounded research, then `emkeel strategy check`.")
    return 0


def _do_check(topic: str, target: Path) -> int:
    sdir = target / STRATEGY_DIR
    if topic:
        docs = [sdir / f"{slug(topic)}.md"]
    else:
        docs = sorted(p for p in sdir.glob("*.md")) if sdir.is_dir() else []
    docs = [d for d in docs if d.is_file()]
    if not docs:
        print("  No strategy docs to check.")
        return 0
    ok = True
    for d in docs:
        problems = lint_strategy(d.read_text(encoding="utf-8"))
        if problems:
            ok = False
            print(f"✗ {d.relative_to(target)}:")
            for p in problems:
                print(f"    - {p}", file=sys.stderr)
        else:
            print(f"✓ {d.relative_to(target)}")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    target = Path(".")
    sub = argv[0] if argv else ""
    rest = argv[1:]
    if sub == "new":
        return _do_new(rest[0] if rest else "", target)
    if sub == "check":
        return _do_check(rest[0] if rest else "", target)
    print("usage: emkeel strategy <new <topic> | check [topic]>", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
