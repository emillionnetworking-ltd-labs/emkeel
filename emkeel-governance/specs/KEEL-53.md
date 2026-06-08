# KEEL-53 — spinner for the quick configuration steps

## Context
During connect/eject the quick gh-api steps printed nothing while running, then a result line.
A spinner makes it feel responsive ("configuring…") without losing the result. The git push must
stay visible (terminal-inherited) — never hidden behind a spinner (that caused the silent hang).

## Plan
- `src/emkeel/ui.py` — `spin(label)` context manager: animates on a TTY, no-op off a TTY (CI/pipes
  /tests). `connect.py` wraps create+push, branch protection, verify creds, save secrets, auto-merge.
  `uninstall.py` wraps remote_cleanup's drop-protection + delete-secrets. The push stays visible.
  `tests/test_ui.py`. Bump 0.1.37.

## Acceptance Criteria
- The quick gh steps show a spinner on a TTY and a ✓/✗ result; off a TTY there's no animation.
- The git push is never wrapped in the spinner (stays visible).

## Anti-regression
- Tests: spin is a no-op off a TTY (body runs, nothing written); the existing connect/eject tests
  still pass (spin is transparent).
