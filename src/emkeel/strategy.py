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

IMPACT_LEVELS = ("low", "medium", "high")
# `Impact: low` lets a trivial strategy pass `critiqued` with a single lens; absent or anything else → high
# (the full ≥3-lens panel). Non-evasible: you must consciously declare `low` to get the cheap path.
_RE_IMPACT = re.compile(r"(?im)^\s*Impact:\s*(low|medium|high)\b")
FULL_PANEL_LENSES = 3       # non-trivial strategies need ≥ this many distinct adversarial lenses

# A repo source: a CLEAN path (no spaces/prose) with a `/` separator and a `.ext`, optionally followed by
# `:NN` or `:NN-MM` (line / range). With a line → resolve file + line/range; without a line → existence only.
# The `/` requirement (checked in classify_source) keeps bare filenames and prose citations off this path.
_RE_REPO = re.compile(r"^(?P<path>[\w./\-]+\.[A-Za-z0-9]+)(?::(?P<a>\d+)(?:-(?P<b>\d+))?)?$")
# URL *intent*: starts with http/https as a word. Well-formedness is judged separately (urlparse), so a
# typo'd `https//host` is still recognised as a URL and FAILs as malformed instead of passing as external.
_RE_URL_INTENT = re.compile(r"(?i)^https?\b")


def slug(topic: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", topic.strip().lower()).strip("-")
    return s or "strategy"


def doc_impact(text: str) -> str:
    """The declared `Impact:` (low|medium|high) of a strategy doc — defaults to 'high' when absent or
    unrecognized, so omitting it never dodges the full critique panel; only an explicit `low` lowers the bar."""
    m = _RE_IMPACT.search(text or "")
    return m.group(1).lower() if m else "high"


def skeleton(topic: str) -> str:
    return f"""# Strategy: {topic}

Status: DRAFT
Strategy: {slug(topic)}   <!-- feature specs reference this with a `Strategy: {slug(topic)}` line -->
Impact: medium   <!-- low | medium | high — `low` lets a trivial strategy pass critiqued with 1 lens; absent = high (full ≥3-lens panel) -->

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
    if "/" in s and _RE_REPO.fullmatch(s):          # clean repo path (a bare filename or prose stays external)
        return "repo"
    return "external"


def _url_problem(src: str) -> str | None:
    """Offline well-formedness check (stdlib only, no network). None = well-formed."""
    p = urlparse(src.strip())
    if p.scheme.lower() not in ("http", "https") or not p.netloc:
        return "malformed URL (need scheme://host)"
    return None


def _repo_problem(src: str, repo_root: Path) -> str | None:
    """Resolve a `path[:line[-line]]` source against the repo root. None = it resolves.

    With a line → file must exist AND the line/range must be in range. Without a line → existence only
    (so an invented bare path can't dodge resolution just by omitting the line)."""
    m = _RE_REPO.fullmatch(src.strip())
    if not m:                                            # not reached via classify_source, but be safe
        return "not a resolvable repo path"
    path = m.group("path")
    f = repo_root / path
    if not f.is_file():
        return f"file not found: {path}"
    if m.group("a") is None:                             # path-only (no line) → existence is enough
        return None
    a = int(m.group("a"))
    b = int(m.group("b")) if m.group("b") else None
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


# ── /strategy as the first adopter of the generic governed-process engine ──────────────────────────
#
# The skill stops being "prose + an exit gate" and becomes a prereq-gated state machine: you cannot
# reach `approved` without passing through every step in order, and each step's evidence is recorded.
# The engine REFUSES to skip — so an obligatory step can't be silently omitted.

def _researched_provenance(fields: dict) -> tuple[bool, str]:
    """`researched` gate: research must cite provenance. ≥1 VERIFIABLE external source (a URL or a repo
    file:line in `sources`) OR an explicit `internal_only=true`. Subsumes the research-provenance gap:
    an agent can't claim 'researched' with no real source and no internal-only declaration."""
    srcs = fields.get("sources") or []
    if isinstance(srcs, str):
        srcs = [srcs]
    if any(classify_source(str(s)) in ("url", "repo") for s in srcs):
        return True, ""
    if fields.get("internal_only") is True:
        return True, ""
    return False, ("requires provenance — ≥1 external source (a URL or repo file:line) in `sources`, "
                   "OR `internal_only=true` declared explicitly")


def _check_passed(fields: dict) -> tuple[bool, str]:
    """`checked` gate: the deterministic `emkeel strategy check` must have PASSED (recorded)."""
    if fields.get("check_passed") is True:
        return True, ""
    return False, "requires `check_passed=true` (run `emkeel strategy check` and record its pass)"


def critique_lenses(fields: dict) -> list[str]:
    """The distinct adversarial lenses recorded at `critiqued`: each `lens_<angle>=<finding>` field with a
    non-empty finding. One field per lens (not a list) so a finding may contain commas/colons safely."""
    return [k for k in fields if k.startswith("lens_") and str(fields.get(k) or "").strip()]


def _critique_panel(fields: dict) -> tuple[bool, str]:
    """`critiqued` BASELINE (engine): a real adversarial pass, not a one-liner — ≥1 named lens
    (`lens_<angle>=<finding>`) AND a `completeness` critic (what dimension is missing, or 'none'). The CI gate
    raises the floor to ≥3 lenses for non-trivial strategies (by the doc's `Impact:`); this baseline kills the
    silent one-line critique at the engine, and makes a lens-less `critiqued` reachable ONLY under the old
    schema (so the gate can grandfather legacy without a version stamp)."""
    if not critique_lenses(fields):
        return False, ("requires an adversarial panel — at least one `lens_<angle>=<finding>` "
                       "(e.g. `lens_legal=...`), not a single prose line")
    if not str(fields.get("completeness") or "").strip():
        return False, "requires a `completeness` critic — what dimension is missing (or 'none')"
    return True, ""


# The reality outcome is a CLOSED enum: the human records whether the strategy, applied to a real case,
# passed — `mixed` and `fail` are valid, HONEST records, not gate failures. The gate checks the value is one
# of these, never that it is `pass` (judging "good" is the human's job at approval — the KEEL-104 pattern).
REALITY_OUTCOMES = ("pass", "fail", "mixed")


def _reality_validated(fields: dict) -> tuple[bool, str]:
    """`validated` gate: the strategy was applied to ONE real case and the outcome recorded. Deterministic
    STRUCTURE only — it never judges whether the outcome is 'good'. `evidence_ref` is treated like an option
    Source: a URL must be well-formed; a repo `file:line` or an external citation passes here and the CI gate
    re-resolves a repo ref against the repo root (this predicate has no root at advance time, mirroring how
    `researched` provenance is intent-checked here and resolved by `strategy check`)."""
    outcome = str(fields.get("outcome", "")).strip().lower()
    if outcome not in REALITY_OUTCOMES:
        return False, f"`outcome` must be one of {list(REALITY_OUTCOMES)} — the recorded reality result"
    ref = str(fields.get("evidence_ref", "")).strip()
    if ref.lower() in _PLACEHOLDERS:
        return False, "requires `evidence_ref` — a resolvable proof (repo file:line, URL, or external citation)"
    if classify_source(ref) == "url":
        prob = _url_problem(ref)
        if prob:
            return False, f"`evidence_ref` {ref!r}: {prob}"
    return True, ""


def strategy_process() -> "ProcessSchema":
    """The /strategy process schema: scaffolded → researched → proposed → critiqued → checked →
    validated(reality evidence) → presented(human gate shown) → approved(human gate recorded). Declared as
    data — the generic engine in `emkeel.process` enforces the ordering + evidence; nothing here is
    engine-specific. The `validated` step is the reality bar: a strategy can pass every process step and
    still be wrong, so it must record the outcome of being applied to a real case before it can be approved."""
    from emkeel.process import ProcessSchema, Step
    return ProcessSchema("strategy", (
        Step("scaffolded", requires=("topic", "kill_criteria")),  # + the conditions to ABANDON it, up front
        Step("researched", validate=_researched_provenance),
        Step("proposed", requires=("options",)),          # ≥2 real options recorded
        Step("critiqued", validate=_critique_panel),      # multi-lens adversarial panel + completeness critic
        Step("checked", requires=("check_passed",), validate=_check_passed),
        Step("validated", requires=("case", "method", "outcome", "evidence_ref"),
             validate=_reality_validated),                # REALITY bar: tried on a real case, outcome on record
        Step("presented", requires=("presented_to",)),    # shown to the human (the gate)
        Step("approved", requires=("approved_by",)),      # human decision recorded — the hard gate
    ))


def _process_path(target: Path, topic: str) -> Path:
    return target / STRATEGY_DIR / f"{slug(topic)}.process.json"


def _parse_value(raw: str):
    """`k=v` value → bool/null/int/list/str (lists as [a,b,c]). Stdlib only, like the lifecycle's parser."""
    low = raw.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    if low == "null":
        return None
    try:
        return int(raw)
    except ValueError:
        pass
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        return [_parse_value(x.strip()) for x in inner.split(",")] if inner else []
    return raw


def _do_advance(step: str, topic: str, sets: list[str], target: Path) -> int:
    from emkeel.process import PrereqError, advance_on_disk
    schema = strategy_process()
    if step not in schema.names():
        print(f"unknown step '{step}'. Steps: {' → '.join(schema.names())}", file=sys.stderr)
        return 2
    fields = {}
    for raw in sets:
        if "=" not in raw:
            print(f"--set expects key=value (got {raw!r})", file=sys.stderr)
            return 2
        k, _, v = raw.partition("=")
        fields[k] = _parse_value(v)
    try:
        state = advance_on_disk(schema, _process_path(target, topic), step, fields=fields)
    except PrereqError as e:
        print(f"REFUSED: cannot advance '{slug(topic)}' to '{step}' — {e}", file=sys.stderr)
        return 1
    print(f"✓ {slug(topic)} → {state['state']}  (process: strategy)")
    return 0


def _do_status(topic: str, target: Path) -> int:
    from emkeel.process import read_state, step_done
    schema = strategy_process()
    state = read_state(_process_path(target, topic))
    if state is None:
        print(f"  {slug(topic)}: process not started (no step recorded yet).")
        return 0
    print(f"  {slug(topic)} — process: strategy (current: {state.get('state') or '(none)'})")
    for name in schema.names():
        mark = "✓" if step_done(state, name) else "·"
        print(f"    {mark} {name}")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    target = Path(os.environ.get("EMKEEL_REPO_DIR", "."))
    sub = argv[0] if argv else ""
    rest = argv[1:]
    positional = [a for a in rest if not a.startswith("-")]
    if sub == "new":
        return _do_new(rest[0] if rest else "", target)
    if sub == "check":
        check_urls = "--check-urls" in rest
        return _do_check(positional[0] if positional else "", target, check_urls=check_urls)
    if sub == "advance":
        if not positional:
            print("usage: emkeel strategy advance <step> <topic> [--set k=v ...]", file=sys.stderr)
            return 2
        step = positional[0]
        topic = positional[1] if len(positional) > 1 else ""
        sets = [a[len("--set="):] for a in rest if a.startswith("--set=")]
        return _do_advance(step, topic, sets, target)
    if sub == "status":
        return _do_status(positional[0] if positional else "", target)
    print("usage: emkeel strategy <new <topic> | check [topic] [--check-urls] | "
          "advance <step> <topic> [--set k=v] | status <topic>>", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
