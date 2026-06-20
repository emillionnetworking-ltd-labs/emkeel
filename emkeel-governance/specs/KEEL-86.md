# KEEL-86 — Exempt the `dependabot/*` lane from the Jira-ticket requirement (sibling of `emkeel-maint/*`)

## Context
Dependabot PRs land on `dependabot/<ecosystem>/...` branches created by a bot — they carry no Jira ticket.
The `check_ticket_link` existence gate (KEEL-83) therefore blocks them. This is shared governance: it lives
in emkeel and every governed repo inherits it (em-ecosystem picks it up via `pip install emkeel` in CI).

The pattern already exists for `emkeel-maint/*`: `lanes.py` (`is_maint_lane` + `MAINT_PREFIX`, KEEL-85) is
the single source of truth, and `check_maint_scope` keeps that lane honest (it may touch only
emkeel-managed files). This replicates the pattern for Dependabot, with its own honest scope.

## Plan
1. **`lanes.py`** — add `DEPENDABOT_PREFIX = "dependabot/"` + `is_dependabot_lane(branch)`. `lanes.py` stays
   the ONLY source of truth for the lanes.
2. **`check_ticket_link`** — exempt `dependabot/*` too (via `is_dependabot_lane`), exactly as it already
   does for `is_maint_lane`.
3. **`jira.py`** (post-merge transition) — SKIP on `dependabot/*` (no ticket → exit 0), so the lane doesn't
   produce the false-red we fixed for maint in KEEL-85.
4. **`check_dependabot_scope`** (new gate, sibling of `check_maint_scope`) — keeps the lane honest: a
   `dependabot/*` PR may touch ONLY dependency files (manifests/lockfiles across npm/pip/ruby/go/rust/php/
   .NET) + GitHub Actions workflow bumps + the dependabot config. Anything else → FAIL. So `dependabot/`
   can't be used as a ticket bypass to smuggle code. Reuses `check_maint_scope.changed_files` (one source
   of the base diff). Wired into `ci.yml` + the scaffolded `_ci_yaml`.

## Invariants
- `lanes.py` is the single source of the lane rule; every site imports the predicate, no hardcoded copies.
- The exemption is ONLY of the Jira ticket — Dependabot PRs still pass every other gate (tests / audit /
  security / SAST). The scope gate makes the exemption safe.
- `emkeel-maint/*` behavior is unchanged.

## Acceptance Criteria
1. `is_dependabot_lane`: `dependabot/*` → True; normal / maint / empty / None → False; canonical prefix.
2. `check_ticket_link` exempts `dependabot/*` (no ticket required); a normal branch with no ticket still
   FAILS; `emkeel-maint/*` still exempt.
3. `jira` transition on `dependabot/*` → SKIP (exit 0), never reaching `transition_issue`.
4. `check_dependabot_scope`: a `dependabot/*` touching only dependency files → OK; touching code → FAIL;
   a non-dependabot branch → N/A.
5. The scaffolded CI (`_ci_yaml`) wires the new gate.

## Sequencing
Branched off main at 0.1.71; bumps to **0.1.72**. No ADR — it's the sibling of the maint exemption, not a
new architectural decision.
