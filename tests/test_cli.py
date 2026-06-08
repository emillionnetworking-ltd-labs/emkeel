"""Tests for the emkeel CLI dispatcher."""

from emkeel.cli import main


def test_no_args_prints_usage(capsys):
    assert main([]) == 0
    assert "usage: emkeel" in capsys.readouterr().out


def test_unknown_command(capsys):
    assert main(["bogus"]) == 2
    assert "unknown command" in capsys.readouterr().err


def test_onboard_prints_playbook(capsys):
    assert main(["onboard"]) == 0
    out = capsys.readouterr().out
    assert "paste" in out.lower()        # the human "paste to your agent" header
    assert "onboarding" in out.lower()   # the playbook content


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
