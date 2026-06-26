# 10. A governed strategy is retired by deleting its doc and process sidecar as a pair

- Status: accepted
- Date: 2026-06-26
- Deciders: operator (EMillion Networking)
- Ticket: KEEL-115

## Context

ADR-0005 made `/strategy` a non-skippable governed process and KEEL-100 added `check_strategy_process`: when
a PR touches `emkeel-governance/strategy/<topic>.md`, a committed `<topic>.process.json` must exist and have
reached `≥checked` (with `researched` provenance). That gate only knows one shape of change — a strategy
being created or refined. It has no notion of a strategy being **retired**.

But strategies do get retired: a path is tried, found not to work, and removed from the repo. Deleting the
`<topic>.md` together with its `<topic>.process.json` is the honest way to do that. The gate FAILed it: it
iterates the changed `.md` (deletes included, via `git diff --name-only`), looks for each sidecar on disk,
and reports "governed-process state missing" — because in a retiro the sidecar is gone. A governed process
could be *completed* but never *ended*; there was no way to express "this strategy is withdrawn".

## Decision

`check_strategy_process` recognizes **retiro** as a first-class operation, with one rule: a strategy is
retired by deleting its doc and its process sidecar **as a pair**.

- **Clean retiro → OK**: the diff DELETES `<topic>.md` and `<topic>.process.json` (the sidecar absent on
  disk) → the gate passes. A governed process can be ended, not only completed.
- **Anti-orphan → FAIL**: `<topic>.md` deleted while the sidecar survives → FAIL. A process state with no
  doc is an orphan (incoherent governance); the retiro must remove the pair.
- **ADD/EDIT unchanged**: an added or modified strategy still requires its sidecar at `≥checked` with
  `researched` provenance — the existing strict path is not weakened.

Detection is deterministic and reuses the gate's git plumbing: a new `deleted_files(base)`
(`git diff --diff-filter=D --name-only`) distinguishes a delete from an edit, which `--name-only` alone
cannot. `check_strategy_change` already forces a strategy change onto a `strategy/<KEY>` lane with a ticket,
so a retiro is still a deliberate, traceable act — this ADR only teaches the *process* gate that a paired
deletion is valid.

## Consequences

- **Strategies can be withdrawn cleanly**: the operator can delete a doc+sidecar pair in a `strategy/<KEY>`
  lane and the gate passes, instead of being stuck because the sidecar it demands no longer exists.
- **Coherence preserved**: the doc and its governed-process state are kept in lockstep — neither a doc
  without a process nor a process without a doc can merge.
- **No weakening of the forward path**: creation/refinement still proves the process ran to `checked` with
  real provenance; retiro is an additional recognized operation, not a loophole.
- **Reusable plumbing**: `deleted_files` lives beside `changed_files`, available to any future gate that
  must treat removal differently from edition.
