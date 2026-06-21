"""Tests for the emkeel CLI dispatcher."""

import emkeel.cli as climod
from emkeel.cli import main


def test_no_args_prints_usage(capsys):
    assert main([]) == 0
    assert "usage: emkeel" in capsys.readouterr().out


# ── proactive nudge (KEEL-94): cheap, fail-safe, bilingual hint on any command ──

def test_nudge_fires_when_pending(monkeypatch, capsys):
    monkeypatch.delenv("EMKEEL_NO_UPDATE_CHECK", raising=False)
    monkeypatch.setattr("emkeel.doctor.wiring_nudge", lambda *a, **k: "⚠ wiring out of date → emkeel update")
    main(["review"])                                   # any non-exempt command
    assert "emkeel update" in capsys.readouterr().err  # nudge to stderr


def test_nudge_silent_when_up_to_date(monkeypatch, capsys):
    monkeypatch.setattr("emkeel.doctor.wiring_nudge", lambda *a, **k: None)
    main(["review"])
    assert "wiring" not in capsys.readouterr().err


def test_nudge_skipped_for_exempt_commands(monkeypatch, capsys):
    called = {"n": 0}
    monkeypatch.setattr("emkeel.doctor.wiring_nudge", lambda *a, **k: called.update(n=called["n"] + 1) or "x")
    for c in ("doctor", "update", "connect", "guard", "version"):
        climod._maybe_nudge(c)
    assert called["n"] == 0                             # never queried for exempt commands


def test_nudge_respects_no_update_check(monkeypatch, capsys):
    monkeypatch.setenv("EMKEEL_NO_UPDATE_CHECK", "1")
    monkeypatch.setattr("emkeel.doctor.wiring_nudge", lambda *a, **k: "should not appear")
    climod._maybe_nudge("review")
    assert "should not appear" not in capsys.readouterr().err


def test_nudge_is_fail_safe(monkeypatch, capsys):
    monkeypatch.setattr("emkeel.doctor.wiring_nudge", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    climod._maybe_nudge("review")                       # must not raise
    assert main(["review"]) == 2                        # command still runs normally


def test_unknown_command(capsys):
    assert main(["bogus"]) == 2
    assert "unknown command" in capsys.readouterr().err

def test_init_dispatch(tmp_path):
    assert main(["init", str(tmp_path), "--dry-run"]) == 0


def test_review_dispatch_returns_usage_without_key():
    # review.main returns 2 (usage) when no key is given
    assert main(["review"]) == 2


def test_eject_and_uninstall_alias(tmp_path):
    # `eject` is the command; `uninstall` is the backward-compat alias (eject is interactive
    # by default now, so use --dry-run here to test the dispatch without prompting).
    assert main(["eject", str(tmp_path), "--dry-run"]) == 0
    assert main(["uninstall", str(tmp_path), "--dry-run"]) == 0
