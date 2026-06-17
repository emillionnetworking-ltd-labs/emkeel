# KEEL-78 — Harden `emkeel strategy check`: verify Sources resolve (not just non-empty)

## Context
Layer 2's anti-hallucination gate used to check only that an option's `Source` cell was non-empty. An
agent could therefore cite a plausible-but-false `file:line` or URL and pass the gate — an ungrounded
strategy slipping through, exactly what emkeel exists to stop. This ticket makes the gate *resolve* each
source, deterministically and offline (stdlib only).

Sources are classified into three kinds, each with its own verdict:

1. **Repo path with line** (`path/file.ext:NN` or `:NN-MM`, or `file.ext:NN`) — MUST resolve against the
   repo root: the file exists and the line/range is within the file's line count. Else **FAIL**.
2. **URL** (`http://` / `https://`) — MUST be syntactically well-formed (stdlib `urllib.parse`, no network).
   Malformed → **FAIL**. Reachability is never checked in the default path (the gate is hermetic/offline).
   `emkeel strategy check --check-urls` opts into a non-blocking `HEAD` for *local* use; failures there are
   **WARN**, never FAIL.
3. **External / unverifiable** (free text that is neither a repo path nor a URL — e.g. `AUTH-v2.md §5 D-002`,
   citations to frozen out-of-tree repos) — cannot be verified deterministically → **WARN** (non-blocking),
   counted in the summary so the human sees it at the gate.

## Plan
- `src/emkeel/strategy.py`
  - `classify_source` / `_url_problem` / `_repo_problem` — pure source classification + resolution (stdlib
    `re`, `pathlib`, `urllib.parse`).
  - `_structural_problems` — factor out the section/`≥2 options` checks shared by lint + review.
  - `lint_strategy(text, repo_root=None)` — back-compatible; resolves repo paths only when a `repo_root` is
    given (pure-text callers pass none and keep skipping resolution).
  - `review_strategy(text, repo_root)` — returns `(fails, warns, unverifiable_count)` so the CLI can print
    FAIL vs WARN per doc.
  - `_do_check` — resolves against `target` (repo root), prints FAIL/WARN per doc + an `N sources
    unverifiable` summary; `--check-urls` flag (WARN-only HEAD, opt-in).
- `src/emkeel/gates/check_strategy_quality.py` — repo root injectable via `EMKEEL_REPO_DIR` (default `.`),
  flowing into `_do_check`. Still dormant when there are no strategy docs.
- Tests for all six acceptance cases incl. an `auth.md` fixture replicating em-ecosystem's approved doc
  (file:line + NIST/FIDO/RFC9700 URLs + an external frozen-repo citation). Bump 0.1.64.

## Acceptance Criteria
1. A `file:line` that resolves → PASS; a nonexistent file → FAIL; a line/range out of range → FAIL.
2. A well-formed URL → PASS; a malformed URL → FAIL; no network in the default path.
3. An external/unverifiable source → WARN (not FAIL) and counted in the summary.
4. The `auth.md` fixture (replicating the real mix) still PASSES — its external citations are WARN, not FAIL.
5. The gate stays dormant when there are no strategy docs (unchanged).
6. `emkeel strategy check` output distinguishes FAIL from WARN, per document.
7. New tests cover the six cases above; coverage is maintained (≥85% branch / ≥90% line).

## Anti-regression
- `repo_root=None` keeps `lint_strategy(text)` behaviour for pure-text callers (no resolution).
- The `auth.md` real-mix fixture is a permanent regression guard: if resolution ever turns its legitimate
  external citations into a FAIL, the design is wrong.
- Zero-dependency, deterministic, hermetic: only stdlib; no network unless `--check-urls` is passed locally.
