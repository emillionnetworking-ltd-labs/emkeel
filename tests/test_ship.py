"""Tests for `emkeel ... --ship` — governance-respecting auto-commit/push/PR/auto-merge."""

from types import SimpleNamespace

from emkeel.init import Config, apply
from emkeel.ship import ship, ship_key_from


def _fake_run(calls):
    def run(args, **kw):
        calls.append(" ".join(args))
        return SimpleNamespace(returncode=0, stdout="https://github.com/o/r/pull/1", stderr="")
    return run


def test_ship_key_from():
    assert ship_key_from(["--ship", "KEEL-9"]) == "KEEL-9"
    assert ship_key_from(["jira-project", "ECO", "--ship", "KEEL-9"]) == "KEEL-9"
    assert ship_key_from(["--ship"]) == ""
    assert ship_key_from(["foo"]) is None


def test_ship_runs_full_governance_flow(tmp_path):
    apply(tmp_path, Config(github_repo="o/r"), force=False, dry_run=False)
    calls = []
    assert ship("KEEL-9", ["emkeel.toml"], target=tmp_path, run=_fake_run(calls)) == 0
    j = "\n".join(calls)
    assert "checkout -b chore/KEEL-9-emkeel-update" in j   # branch
    assert "commit -m" in j                                # commit
    assert "git push -u origin HEAD" in j                  # push
    assert "gh pr create" in j                             # PR
    assert "gh pr merge --auto" in j                       # native auto-merge (gates decide)


def test_ship_rejects_bad_key(tmp_path):
    assert ship("not-a-key", ["emkeel.toml"], target=tmp_path, run=lambda *a, **k: None) == 2


def test_ship_noop_when_no_paths(tmp_path):
    calls = []
    assert ship("KEEL-9", [], target=tmp_path, run=_fake_run(calls)) == 0
    assert calls == []                                     # nothing touched
