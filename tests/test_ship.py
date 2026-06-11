"""Tests for ship() — the scope-gated emkeel-maint auto-ship lane."""

from types import SimpleNamespace

from emkeel.init import Config, apply
from emkeel.ship import ship


def _fake_run(calls, dirty=" M emkeel.toml"):
    def run(args, **kw):
        calls.append(" ".join(str(a) for a in args))
        j = " ".join(args)
        out = ""
        if "status --porcelain" in j:
            out = dirty
        elif "rev-parse --short" in j:
            out = "abc123"
        elif "rev-parse --abbrev-ref" in j:
            out = "main"
        elif "default_branch" in j:
            out = "main"
        elif "symbolic-ref" in j:
            out = "refs/remotes/origin/main"
        elif "pr create" in j:
            out = "https://github.com/o/r/pull/1"
        return SimpleNamespace(returncode=0, stdout=out, stderr="")
    return run


def test_ship_full_maint_flow(tmp_path):
    apply(tmp_path, Config(github_repo="o/r"), force=False, dry_run=False)
    calls = []
    assert ship(["emkeel.toml"], target=tmp_path, run=_fake_run(calls)) == 0
    j = "\n".join(calls)
    assert "checkout -B emkeel-maint/" in j and "origin/main" in j   # forked from default
    assert "commit -m" in j
    assert "git push -u origin HEAD" in j
    assert "gh pr create" in j
    assert "gh pr merge --auto" in j


def test_ship_refuses_other_uncommitted_changes(tmp_path):
    apply(tmp_path, Config(github_repo="o/r"), force=False, dry_run=False)
    calls = []
    rc = ship(["emkeel.toml"], target=tmp_path,
              run=_fake_run(calls, dirty=" M emkeel.toml\n M src/app.py"))
    assert rc == 1                                       # stray src/app.py → refuse
    assert not any("pr create" in c for c in calls)


def test_ship_noop_when_no_paths(tmp_path):
    assert ship([], target=tmp_path,
                run=lambda *a, **k: SimpleNamespace(returncode=0, stdout="", stderr="")) == 0
