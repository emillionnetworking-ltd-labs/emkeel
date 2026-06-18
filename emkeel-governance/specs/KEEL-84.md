# KEEL-84 — `emkeel update` async-window UX: in-flight maint PR awareness

## Context
`emkeel update` does NOT apply the change to your working tree — it ships it through the
`emkeel-maint/<version>-<sha>` lane → PR → auto-merge (lands when CI passes, ~minutes). The command
returns in seconds. During that window, two real rough edges appear:

- **(A)** `emkeel doctor` reads the still-old local working tree → reports drift and says
  "→ run: emkeel update", nagging you to redo what you just did.
- **(B)** Re-running `emkeel update` fails with `non-fast-forward` because the `emkeel-maint/*` branch
  already exists on the remote (a second run pushes a different commit onto the same lane).

## Plan (lib + thin CLI; gh boundary injected; graceful degradation)
1. **`inflight_maint_pr(repo, run)`** in `ship.py` — pure, testable: returns the number of an OPEN PR
   whose head is an `emkeel-maint/*` lane, else None. Degrades to None when gh is unavailable/errors.
2. **`_ship_via_worktree` checks it before pushing** (fixes B): if a maint PR is already in flight, print
   "Already shipped as PR #N, pending auto-merge — nothing re-pushed. Run `git pull` once it lands." and
   exit 0, WITHOUT re-pushing. `emkeel update` flows through here, so no `update.py` change is needed.
   (`--no-ship` is unaffected — it never enters the ship path.)
3. **`doctor` reports the in-flight refresh** (fixes A): when there is wiring drift AND an open
   `emkeel-maint/*` PR resolves it, doctor says "⚠ N wiring file(s) out of date — refresh in flight
   (PR #N); will be clean after it merges + `git pull`." instead of "→ run: emkeel update". No PR → the
   current message.
4. **Async note on a successful ship**: "Note: this applies asynchronously — PR #N merges once CI passes
   (~min). Until then `emkeel doctor` will still show drift here; run `git pull` after it merges."

## Degradation
Detecting the in-flight PR needs gh/network. If gh is missing or fails, `inflight_maint_pr` returns None
and both call sites fall back to the prior behavior (ship / "run: emkeel update") — never an error, the
same way absent secrets degrade to a warning elsewhere.

## Invariants
- Lib + thin CLI; `inflight_maint_pr` is pure with the gh boundary injected (zero network in tests).
- The `emkeel-maint/*` scope-gated lane and `--no-ship` behavior are unchanged.

## Acceptance Criteria
1. `inflight_maint_pr`: open maint PR → its number; only non-maint PRs → None; gh failure → None; bad
   JSON → None; empty repo → None.
2. `emkeel update` with an in-flight maint PR → prints "Already shipped as PR #N", exits 0, does NOT
   re-push / re-open a PR.
3. `emkeel update` with no in-flight PR → normal ship (unchanged).
4. `doctor` with drift + in-flight PR → "refresh in flight (PR #N)"; with drift + no PR → "run: emkeel
   update".
5. Degradation: gh unavailable → doctor falls back to "run: emkeel update"; ship proceeds normally.
6. A successful ship prints the async note.

## Sequencing note
Branched off main at 0.1.68; bumps to **0.1.70** (KEEL-83 / PR #85 holds 0.1.69). Merge this after #85;
the version line may need a trivial rebase.
