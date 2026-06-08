# KEEL-55 — onboard playbook covers removal (eject + uninstall)

## Context
The agent playbook only covered adopting Emkeel. The AI should also be able to guide removal.

## Plan
- `src/emkeel/_docs/onboarding.md` — add a "Removing Emkeel" section: AI asks what to remove
  (wiring / governance / GitHub side, translated), runs `emkeel eject --yes` + flags
  (`--purge`/`--remote`/`--all`) deterministically (push stays visible), then `pipx uninstall emkeel`
  (confirm first; order: eject before uninstall; uninstalling ≠ un-governing). `tests/test_cli.py`.
  Bump 0.1.40.

## Acceptance Criteria
- The printed playbook includes the removal flow (eject + uninstall) and the order/caveat.

## Anti-regression
- Test asserts the onboard output mentions `setup --json` and `eject`.
