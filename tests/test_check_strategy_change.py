"""Tests for the strategy-change gate: the north star (strategy/*.md) is lane-gated."""

import emkeel.gates.check_strategy_change as g

SDIR = "emkeel-governance/strategy"


def _run(monkeypatch, files, branch, base="main", strategy_dir=None):
    """Drive g.main() with a fixed changed-files list + branch env (no real git)."""
    monkeypatch.setattr(g, "changed_files", lambda base, **k: list(files))
    monkeypatch.setenv("EMKEEL_BRANCH", branch)
    monkeypatch.setenv("EMKEEL_BASE_REF", base)
    if strategy_dir is not None:
        monkeypatch.setenv("EMKEEL_STRATEGY_DIR", strategy_dir)
    else:
        monkeypatch.delenv("EMKEEL_STRATEGY_DIR", raising=False)
    return g.main()


# ── pure filter ────────────────────────────────────────────────────────────────

def test_strategy_docs_changed_filters_md_only():
    files = [
        f"{SDIR}/auth.md", f"{SDIR}/.gitkeep", f"{SDIR}/notes.txt",
        "src/emkeel/strategy.py", f"{SDIR}/sub/deep.md",
    ]
    assert g.strategy_docs_changed(files, SDIR) == [f"{SDIR}/auth.md", f"{SDIR}/sub/deep.md"]


# ── AC1: feat/ editing a strategy doc → FAIL ───────────────────────────────────

def test_feature_editing_strategy_fails(monkeypatch):
    assert _run(monkeypatch, [f"{SDIR}/auth.md"], "feat/KEEL-50-thing") == 1


# ── AC2: strategy/ lane with a ticket → PASS ───────────────────────────────────

def test_strategy_lane_with_ticket_passes(monkeypatch):
    assert _run(monkeypatch, [f"{SDIR}/auth.md"], "strategy/KEEL-99-foo") == 0


# ── AC3: branch not touching strategy → N/A ────────────────────────────────────

def test_no_strategy_change_is_na(monkeypatch):
    assert _run(monkeypatch, ["src/emkeel/cli.py", "README.md"], "feat/KEEL-50-thing") == 0


# ── AC4: only .gitkeep / non-md under strategy → N/A (does not trigger) ─────────

def test_gitkeep_or_nonmd_does_not_trigger(monkeypatch):
    assert _run(monkeypatch, [f"{SDIR}/.gitkeep", f"{SDIR}/notes.txt"], "feat/KEEL-50-thing") == 0


# ── AC5: DELETE of a strategy doc on feat/ → FAIL (git diff lists deletions too) ─

def test_feature_deleting_strategy_fails(monkeypatch):
    # `git diff --name-only` reports a deleted path the same way — deleting the north is changing it.
    assert _run(monkeypatch, [f"{SDIR}/auth.md", "src/x.py"], "fix/KEEL-50-thing") == 1


# ── AC6: strategy/ lane WITHOUT a ticket key → FAIL (traceability) ──────────────

def test_strategy_lane_without_ticket_fails(monkeypatch):
    assert _run(monkeypatch, [f"{SDIR}/auth.md"], "strategy/no-ticket-here") == 1


# ── AC7: EMKEEL_STRATEGY_DIR injectable ────────────────────────────────────────

def test_strategy_dir_injectable(monkeypatch):
    # a custom dir: a doc under it triggers; the default dir is then irrelevant.
    assert _run(monkeypatch, ["custom/strat/auth.md"], "feat/KEEL-1-x", strategy_dir="custom/strat") == 1
    assert _run(monkeypatch, ["custom/strat/auth.md"], "strategy/KEEL-1-x", strategy_dir="custom/strat") == 0
    # a doc under the DEFAULT dir does not trigger when the configured dir is elsewhere.
    assert _run(monkeypatch, [f"{SDIR}/auth.md"], "feat/KEEL-1-x", strategy_dir="custom/strat") == 0


# ── first-ever strategy creation also goes through the lane (not dormant-by-existence) ─

def test_first_creation_must_use_lane(monkeypatch):
    assert _run(monkeypatch, [f"{SDIR}/brand-new.md"], "feat/KEEL-1-first") == 1
    assert _run(monkeypatch, [f"{SDIR}/brand-new.md"], "strategy/KEEL-1-first") == 0
