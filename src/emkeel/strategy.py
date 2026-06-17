"""emkeel strategy — scaffold + lint researched strategy artifacts.

  emkeel strategy new <topic>    scaffold emkeel-governance/strategy/<topic>.md (required structure)
  emkeel strategy check [topic]  lint strategy docs: required sections + EVERY option's Source RESOLVES

The `/strategy` skill fills the scaffold via grounded research; `check` is the deterministic gate
that catches an ungrounded/hallucinated doc. "done" = check passes, not prose. Beyond "the cell is
non-empty", `check` now *resolves* each Source: a repo `file:line` must exist (file + line in range),
a URL must be syntactically well-formed (offline, stdlib only), and a free-text external citation that
can't be verified deterministically is surfaced as a WARN for the human gate — never a silent pass.
This module is pure + tested; the skill is a thin prose orchestrator on top.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

STRATEGY_DIR = "emkeel-governance/strategy"
REQUIRED_SECTIONS = ("Goal", "Context", "Options", "Recommendation")
_PLACEHOLDERS = {"", "-", "—", "tbd", "todo", "n/a", "<source>"}

# A repo source: a path ending in a `.ext`, then `:NN` or `:NN-MM` (line / range). The line is required;
# a bare path without a line is treated as external (unverifiable) rather than a repo source.
_RE_REPO = re.compile(r"^(?P<path>[\w./\-]+\.[A-Za-z0-9]+):(?P<a>\d+)(?:-(?P<b>\d+))?$")
# URL *intent*: starts with http/https as a word. Well-formedness is judged separately (urlparse), so a
# typo'd `https//host` is still recognised as a URL and FAILs as malformed instead of passing as external.
_RE_URL_INTENT = re.compile(r"(?i)^https?\b")


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


def classify_source(src: str) -> str:
    """'url' | 'repo' | 'external' for a Source cell. Detection is by *intent*, not validity:
    a malformed URL still classifies as 'url' (so it FAILs as malformed, not silently passes)."""
    s = src.strip()
    if _RE_URL_INTENT.match(s):
        return "url"
    if _RE_REPO.fullmatch(s):
        return "repo"
    return "external"


def _url_problem(src: str) -> str | None:
    """Offline well-formedness check (stdlib only, no network). None = well-formed."""
    p = urlparse(src.strip())
    if p.scheme.lower() not in ("http", "https") or not p.netloc:
        return "malformed URL (need scheme://host)"
    return None


def _repo_problem(src: str, repo_root: Path) -> str | None:
    """Resolve a `path:line[-line]` source against the repo root. None = it resolves."""
    m = _RE_REPO.fullmatch(src.strip())
    if not m:                                            # not reached via classify_source, but be safe
        return "not a resolvable file:line source"
    path, a = m.group("path"), int(m.group("a"))
    b = int(m.group("b")) if m.group("b") else None
    f = repo_root / path
    if not f.is_file():
        return f"file not found: {path}"
    n = len(f.read_text(encoding="utf-8", errors="replace").splitlines())
    if a < 1 or a > n:
        return f"line {a} out of range ({path} has {n} lines)"
    if b is not None and (b < a or b > n):
        return f"line range {a}-{b} out of range ({path} has {n} lines)"
    return None


def _structural_problems(text: str) -> tuple[list[str], list[dict]]:
    """Section + option-count checks (independent of source resolution). Returns (problems, filled_rows)."""
    problems = []
    for sec in REQUIRED_SECTIONS:
        if not re.search(rf"(?im)^\s*#+\s*{sec}\b", text):
            problems.append(f"missing section: ## {sec}")
    filled = [r for r in _option_rows(text) if r["option"]]
    if len(filled) < 2:
        problems.append("Options needs at least 2 filled options (research the alternatives)")
    return problems, filled


def _source_issues(filled: list[dict], repo_root: Path | None) -> tuple[list[str], list[str], int]:
    """Resolve every option's Source → (fails, warns, unverifiable_count).

    repo paths FAIL when they don't resolve; URLs FAIL when malformed; external citations WARN (can't be
    verified deterministically). When repo_root is None (pure-text callers), repo paths are skipped, not
    failed — resolution needs a root to resolve against."""
    fails, warns, unverifiable = [], [], 0
    for r in filled:
        src = r["source"].strip()
        opt = r["option"][:40]
        if src.lower() in _PLACEHOLDERS:
            fails.append(f"option '{opt}' has no Source — cite a file:line or URL")
            continue
        kind = classify_source(src)
        if kind == "url":
            prob = _url_problem(src)
            if prob:
                fails.append(f"option '{opt}' source {src!r}: {prob}")
        elif kind == "repo":
            if repo_root is None:
                continue
            prob = _repo_problem(src, repo_root)
            if prob:
                fails.append(f"option '{opt}' source {src!r}: {prob}")
        else:                                            # external — not deterministically verifiable
            unverifiable += 1
            warns.append(f"option '{opt}' source {src!r}: unverifiable (external) — human must confirm")
    return fails, warns, unverifiable


def lint_strategy(text: str, repo_root: Path | None = None) -> list[str]:
    """Deterministic FATAL problems with a strategy doc (empty list = OK). The anti-hallucination check.

    Pass repo_root to resolve `file:line` sources against it; omit it (pure-text lint) to skip that.
    WARN-level findings (unverifiable externals) are not returned here — see review_strategy."""
    problems, filled = _structural_problems(text)
    fails, _warns, _unver = _source_issues(filled, repo_root)
    return problems + fails


def review_strategy(text: str, repo_root: Path | None) -> tuple[list[str], list[str], int]:
    """Full review for the CLI/gate: (fails, warns, unverifiable_count), distinguishing FAIL from WARN."""
    problems, filled = _structural_problems(text)
    fails, warns, unverifiable = _source_issues(filled, repo_root)
    return problems + fails, warns, unverifiable


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


def _url_warnings(text: str) -> list[str]:
    """OPT-IN, local-only: non-blocking HEAD reachability for each URL source. Never FAILs (WARN only).

    Network is touched ONLY here, only when `--check-urls` is passed — the default gate path stays hermetic."""
    import urllib.error
    import urllib.request

    warns = []
    for r in (r for r in _option_rows(text) if r["option"]):
        src = r["source"].strip()
        if classify_source(src) != "url" or _url_problem(src):
            continue
        req = urllib.request.Request(src, method="HEAD")
        try:
            urllib.request.urlopen(req, timeout=5).close()
        except (urllib.error.URLError, OSError, ValueError) as e:
            warns.append(f"option '{r['option'][:40]}' URL {src!r}: unreachable ({e}) — verify manually")
    return warns


def _do_check(topic: str, target: Path, check_urls: bool = False) -> int:
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
    total_unverifiable = 0
    for d in docs:
        text = d.read_text(encoding="utf-8")
        fails, warns, unverifiable = review_strategy(text, target)
        if check_urls:
            warns = warns + _url_warnings(text)
        total_unverifiable += unverifiable
        rel = d.relative_to(target)
        if fails:
            ok = False
            print(f"✗ {rel}:")
            for p in fails:
                print(f"    FAIL: {p}", file=sys.stderr)
        else:
            print(f"✓ {rel}")
        for w in warns:
            print(f"    WARN: {w}")
    if total_unverifiable:
        print(f"  {total_unverifiable} source(s) unverifiable (external) — confirm at the human gate.")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    target = Path(os.environ.get("EMKEEL_REPO_DIR", "."))
    sub = argv[0] if argv else ""
    rest = argv[1:]
    if sub == "new":
        return _do_new(rest[0] if rest else "", target)
    if sub == "check":
        check_urls = "--check-urls" in rest
        positional = [a for a in rest if not a.startswith("-")]
        return _do_check(positional[0] if positional else "", target, check_urls=check_urls)
    print("usage: emkeel strategy <new <topic> | check [topic] [--check-urls]>", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
