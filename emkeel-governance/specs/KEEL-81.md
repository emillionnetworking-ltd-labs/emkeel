# KEEL-81 — Merge-triggered auto-publish to PyPI: the merge IS the gate

## Context
Publishing emkeel was a manual step (`release: published` + `workflow_dispatch`). Operator decision: make
it **full auto, no batching** — every push to `main` auto-publishes, guarded by version. emkeel bumps its
version per feature, so each merge is a new version = a new release. Publishing stops being a human step;
the merge to `main` (already gated by CI + approval + a linked ticket) is the only gate that matters.

Publishing uses PyPI **Trusted Publishing (OIDC)** — already configured, no token.

## Plan — `.github/workflows/release.yml` (emkeel-only)
- Triggers: `on: push: branches: [main]` + `workflow_dispatch`. **Remove `release: published`** — the
  GitHub Release this workflow creates would re-trigger it; the guard would make it idempotent but it
  produces junk runs.
- `concurrency: { group: release, cancel-in-progress: false }` — serialize, never cancel a half-done publish.
- Job `permissions: contents: write` (tag + GitHub Release) + `id-token: write` (OIDC).
- Steps: checkout `fetch-depth: 0` (tags needed for the guard) → setup-python 3.12 → **guard** (read
  `version` from pyproject.toml; if `git rev-parse v$VERSION` exists → `new=false` skip clean success;
  else `new=true`; expose `version`/`new` as outputs) → (if new) build → (if new) publish OIDC → (if new)
  `gh release create v$VERSION --generate-notes --title "Emkeel $VERSION" --target $GITHUB_SHA`.

## Invariants
- **Idempotent**: a push to `main` that does NOT bump the version finds the tag already present → clean
  skip (success, nothing published). It must NOT fail on a duplicate version.
- The guard reads the **tag** as the source of truth, not the network.
- `workflow_dispatch` stays as a manual fallback.
- **`init.py` is NOT touched**: `release.yml` is never scaffolded to product repos (only `emkeel-ci.yml`
  + `jira-transition.yml`). em-ecosystem does not publish to PyPI. Gate logic untouched.

## Transition (first auto-publish happens on THIS merge)
- This PR bumps to **0.1.67**. On merge, the push to `main` triggers the NEW `release.yml`: version 0.1.67
  has no tag → it **publishes 0.1.67** (which contains KEEL-78/79/80 + this automation). Auto notes cover
  everything since **v0.1.63** (the last released tag).
- The intermediate versions **0.1.64 / 0.1.65 / 0.1.66 never exist on PyPI** (non-contiguous — that's fine).
- So the merge of KEEL-81 performs the **first auto-publication**. The workflow must be correct BEFORE
  merging; `workflow_dispatch` is the fallback if something fails.

## Acceptance Criteria
1. `release.yml` triggers on push to `main` + `workflow_dispatch`; `release: published` removed.
2. Guard: publishes only if `v<version>` has no tag; if the tag exists → skip success without publishing.
3. On a new version: build + publish OIDC + create tag `v<version>` + GitHub Release with auto notes.
4. `permissions: contents: write` + `id-token: write`; `concurrency` serializes (no cancel-in-progress).
5. `init.py` unchanged (release stays emkeel-only); gate logic intact.
6. Spec present; bump 0.1.67; gates green; existing Python tests/coverage intact.
